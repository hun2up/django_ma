# django_ma/dash/views.py
from __future__ import annotations

import logging
import re
from datetime import datetime, date
from typing import Optional, Tuple

import pandas as pd
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import SalesRecord

logger = logging.getLogger(__name__)


NONLIFE_INSURERS = {
    "현대해상", "DB손보", "KB손보", "메리츠화재", "한화손보", "롯데손보", "흥국화재",
    "삼성화재", "AIG손보", "MG손보", "농협손보", "하나손보", "라이나손보",
}
LIFE_INSURERS = {
    "ABL생명", "삼성생명", "신한라이프", "하나생명", "IBK연금", "DB생명", "iM라이프",
    "KB라이프생명", "NH농협생명", "라이나생명", "KDB생명", "미래에셋", "처브라이프",
    "한화생명", "카디프생명", "동양생명", "메트라이프", "흥국생명", "푸본현대생명", "교보생명",
}

# ✅ 일반 실적(손보/생보)
REQUIRED_COLS = [
    "소속", "영업가족", "설계사", "설계사CD",
    "보험사", "증권번호", "계약자", "주피",
    "보험시작", "보험종기", "납입방법", "영수일자", "영수금",
    "보험사 상품코드", "보험사 상품명",
]

# ✅ 자동차 실적
AUTO_REQUIRED_COLS = [
    "소속", "파트너", "담당자코드", "담당자명",
    "보험사", "증권번호", "피보험자명", "차량번호",
    "보험기간", "납입방법", "영수일자",
    "책임", "임의", "합계", "상태", "물건구분",
]


@grade_required(["superuser", "main_admin"])
def redirect_to_sales(request):
    return redirect("dash_sales")


# dash/views.py
from django.db.models import Q
import json

@grade_required(["superuser", "main_admin"])
def dash_sales(request):
    now = datetime.now()
    default_year = str(now.year)
    default_month = f"{now.month:02d}"

    # -----------------------------
    # 1) 기간(연/월)
    # -----------------------------
    year = (request.GET.get("year") or default_year).strip()
    month = (request.GET.get("month") or default_month).strip().zfill(2)
    ym = f"{year}-{month}"

    year_options = [str(y) for y in range(now.year - 5, now.year + 2)]
    month_options = [f"{m:02d}" for m in range(1, 13)]

    # -----------------------------
    # 2) 필터 파라미터
    # -----------------------------
    filter_part = (request.GET.get("part") or "").strip()
    filter_branch = (request.GET.get("branch") or "").strip()
    filter_life_nl = (request.GET.get("life_nl") or "").strip()  # 손보/생보/자동차
    filter_insurer = (request.GET.get("insurer") or "").strip()
    filter_q = (request.GET.get("q") or "").strip()
    page = request.GET.get("page", "1")

    try:
        page_size = int(request.GET.get("page_size") or 50)
    except ValueError:
        page_size = 50
    if page_size not in (50, 100, 250, 500):
        page_size = 50

    # -----------------------------
    # 3) base QS: 권한 + 월도(ym)
    # -----------------------------
    qs_base = SalesRecord.objects.all()

    # ✅ main_admin 정책: 본인 지점 데이터만
    if request.user.grade == "main_admin":
        my_branch = (request.user.branch or "").strip()
        if not my_branch:
            qs_base = qs_base.none()
        else:
            qs_base = qs_base.filter(Q(branch_snapshot=my_branch) | Q(user__branch=my_branch))
            filter_branch = my_branch  # 지점은 권한상 고정

    qs_base = qs_base.filter(ym=ym)

    # -----------------------------
    # 4) 조회용 QS (보험사 제외한 상태: qs_pre_insurer)
    #    - insurer_options는 이 QS에서 뽑아야 "손생 연동"이 됨
    # -----------------------------
    qs_pre_insurer = qs_base

    if filter_part:
        qs_pre_insurer = qs_pre_insurer.filter(Q(user__part=filter_part) | Q(part_snapshot=filter_part))

    if filter_branch:
        qs_pre_insurer = qs_pre_insurer.filter(Q(user__branch=filter_branch) | Q(branch_snapshot=filter_branch))

    if filter_life_nl:
        qs_pre_insurer = qs_pre_insurer.filter(life_nl=filter_life_nl)

    if filter_q:
        qs_pre_insurer = qs_pre_insurer.filter(
            Q(policy_no__icontains=filter_q)
            | Q(contractor__icontains=filter_q)
            | Q(name_snapshot__icontains=filter_q)
            | Q(emp_id_snapshot__icontains=filter_q)
            | Q(user__id__icontains=filter_q)
            | Q(user__name__icontains=filter_q)
            | Q(vehicle_no__icontains=filter_q)
        )

    # -----------------------------
    # 5) ✅ 보험사 옵션 캐시(손생/부서/지점/월도 기준)
    #    - q까지 캐시키로 넣으면 캐시 파편화가 심해서 비추
    #    - q가 있을 때만 옵션을 "현 조회결과 기준"으로 즉시 계산(대개 결과가 작음)
    # -----------------------------
    def _clean_list(vals):
        return sorted({str(v).strip() for v in vals if str(v).strip() and str(v).strip().lower() != "nan"})

    insurer_options = []
    if filter_q:
        # 검색 중엔 캐시보다 정확성이 중요 + 결과셋이 작으니 즉시 계산
        insurer_options_raw = list(
            qs_pre_insurer.exclude(insurer__isnull=True).exclude(insurer__exact="")
            .values_list("insurer", flat=True).distinct()
        )
        insurer_options = _clean_list(insurer_options_raw)
    else:
        cache_key = f"dash:insurers:{ym}:{filter_part or '*'}:{filter_branch or '*'}:{filter_life_nl or '*'}"
        insurer_options = cache.get(cache_key)
        if insurer_options is None:
            insurer_options_raw = list(
                qs_pre_insurer.exclude(insurer__isnull=True).exclude(insurer__exact="")
                .values_list("insurer", flat=True).distinct()
            )
            insurer_options = _clean_list(insurer_options_raw)
            cache.set(cache_key, insurer_options, 60 * 30)  # 30분 캐시(원하면 10분/1시간 조절)

    # -----------------------------
    # 6) 최종 조회 QS (보험사 필터 적용)
    # -----------------------------
    qs_final = qs_pre_insurer
    if filter_insurer:
        qs_final = qs_final.filter(insurer=filter_insurer)

    qs_final = qs_final.select_related("user").order_by("-updated_at")

    # -----------------------------
    # 6.5) ✅ 그래프 데이터(2개):
    #  (A) 손생 장기매출: 자동차 제외 + 일시납 제외
    #  (B) 자동차 매출: life_nl='자동차'만 + (일시납 제외는 요구사항에 없음 → 원하면 추가 가능)
    # -----------------------------
    def _build_daily_cumsum(qs):
        qs = qs.order_by().exclude(receipt_date__isnull=True)

        daily_rows = (
            qs.values("receipt_date")
              .annotate(daily_sum=Sum(Coalesce("receipt_amount", 0)))
              .order_by("receipt_date")
        )

        labels, cumsum = [], []
        running = 0
        for row in daily_rows:
            d = row["receipt_date"]
            s = int(row["daily_sum"] or 0)
            running += s
            labels.append(d.strftime("%Y-%m-%d"))
            cumsum.append(running)
        return labels, cumsum

    # (A) 손생(자동차 제외) + 일시납 제외
    qs_chart_long = (
        qs_final
        .exclude(life_nl="자동차")
        .exclude(pay_method__icontains="일시납")
    )
    chart_labels, chart_cumsum = _build_daily_cumsum(qs_chart_long)

    # (B) 자동차만 (요구사항: life_nl='자동차'만)
    qs_chart_car = qs_final.filter(life_nl="자동차")
    car_chart_labels, car_chart_cumsum = _build_daily_cumsum(qs_chart_car)

    # -----------------------------
    # 7) ✅ 부서/지점 옵션: CustomUser + SalesRecord(snapshot + user 필드) "합집합"
    #    - 월도(ym) 기준으로 SalesRecord에서 snapshot도 같이 가져오면,
    #      업로드만 되었고 유저 매핑이 없는 행도 옵션에 자연스럽게 섞임
    # -----------------------------
    # 권한 적용된 월도 기준 SalesRecord subset
    sr_scope = qs_base  # already includes ym + main_admin branch restriction

    # (A) 부서 옵션: CustomUser.part + SalesRecord.part_snapshot + SalesRecord.user.part
    user_part_vals = list(
        CustomUser.objects.exclude(part__isnull=True).exclude(part__exact="")
        .values_list("part", flat=True).distinct()
    )
    # main_admin이면 지점 제한된 사용자만(현실적으로 일치)
    if request.user.grade == "main_admin":
        my_branch = (request.user.branch or "").strip()
        if my_branch:
            user_part_vals = list(
                CustomUser.objects.filter(branch=my_branch)
                .exclude(part__isnull=True).exclude(part__exact="")
                .values_list("part", flat=True).distinct()
            )

    sr_part_snapshot_vals = list(
        sr_scope.exclude(part_snapshot__isnull=True).exclude(part_snapshot__exact="")
        .values_list("part_snapshot", flat=True).distinct()
    )
    sr_user_part_vals = list(
        sr_scope.exclude(user__part__isnull=True).exclude(user__part__exact="")
        .values_list("user__part", flat=True).distinct()
    )

    part_options = _clean_list(user_part_vals + sr_part_snapshot_vals + sr_user_part_vals)

    # (B) 전체 지점 옵션: CustomUser.branch + SalesRecord.branch_snapshot + SalesRecord.user.branch
    user_branch_vals = list(
        CustomUser.objects.exclude(branch__isnull=True).exclude(branch__exact="")
        .values_list("branch", flat=True).distinct()
    )
    if request.user.grade == "main_admin":
        my_branch = (request.user.branch or "").strip()
        user_branch_vals = [my_branch] if my_branch else []

    sr_branch_snapshot_vals = list(
        sr_scope.exclude(branch_snapshot__isnull=True).exclude(branch_snapshot__exact="")
        .values_list("branch_snapshot", flat=True).distinct()
    )
    sr_user_branch_vals = list(
        sr_scope.exclude(user__branch__isnull=True).exclude(user__branch__exact="")
        .values_list("user__branch", flat=True).distinct()
    )

    branch_options_all = _clean_list(user_branch_vals + sr_branch_snapshot_vals + sr_user_branch_vals)

    # (C) part -> branches map (CustomUser + SalesRecord)
    part_branch_map = {}
    for p in part_options:
        # CustomUser 기반
        u_br = list(
            CustomUser.objects.filter(part=p)
            .exclude(branch__isnull=True).exclude(branch__exact="")
            .values_list("branch", flat=True).distinct()
        )
        # main_admin이면 지점 1개로 귀결
        if request.user.grade == "main_admin":
            my_branch = (request.user.branch or "").strip()
            u_br = [my_branch] if my_branch else []

        # SalesRecord snapshot 기반
        sr_br_snap = list(
            sr_scope.filter(part_snapshot=p)
            .exclude(branch_snapshot__isnull=True).exclude(branch_snapshot__exact="")
            .values_list("branch_snapshot", flat=True).distinct()
        )
        # SalesRecord user 기반
        sr_br_user = list(
            sr_scope.filter(user__part=p)
            .exclude(user__branch__isnull=True).exclude(user__branch__exact="")
            .values_list("user__branch", flat=True).distinct()
        )

        part_branch_map[p] = _clean_list(u_br + sr_br_snap + sr_br_user)

    # -----------------------------
    # 8) pagination
    # -----------------------------
    paginator = Paginator(qs_final, page_size)
    page_obj = paginator.get_page(page)

    current_page = page_obj.number
    total_pages = paginator.num_pages
    block_size = 10
    start_page = ((current_page - 1) // block_size) * block_size + 1
    end_page = min(start_page + block_size - 1, total_pages)

    # -----------------------------
    # 9) context
    # -----------------------------
    context = {
        "filter_year": year,
        "filter_month": month,
        "filter_ym": ym,

        "filter_part": filter_part,
        "filter_branch": filter_branch,
        "filter_life_nl": filter_life_nl,
        "filter_insurer": filter_insurer,
        "filter_q": filter_q,

        "year_options": year_options,
        "month_options": month_options,

        # dropdown sources
        "part_options": part_options,
        "branch_options_all": branch_options_all,
        "part_branch_map": part_branch_map,

        # insurer dropdown (손생 연동 + 캐시)
        "insurer_options": insurer_options,

        "page_size": page_size,
        "total_count": qs_final.count(),
        "page_obj": page_obj,
        "start_page": start_page,
        "end_page": end_page,
        "total_pages": total_pages,

        "chart_labels": chart_labels,
        "chart_cumsum": chart_cumsum,

        "car_chart_labels": car_chart_labels,
        "car_chart_cumsum": car_chart_cumsum,
    }
    return render(request, "dash/dash_sales.html", context)


@grade_required(["superuser", "main_admin"])
def dash_recruit(request):
    return render(request, "dash/dash_recruit.html")


@grade_required(["superuser", "main_admin"])
def dash_retention(request):
    return render(request, "dash/dash_retention.html")


# -----------------------------
# 유틸
# -----------------------------
def _json_err(message: str, status: int = 400):
    return JsonResponse({"ok": False, "message": message}, status=status)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # ✅ "물건구분 " 같은 trailing space 방지
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _is_auto_excel(df: pd.DataFrame) -> bool:
    return "물건구분" in df.columns


def _to_date(v) -> Optional[date]:
    if pd.isna(v) or v == "":
        return None

    if isinstance(v, (pd.Timestamp, datetime)):
        try:
            return v.date()
        except Exception:
            return None
    if isinstance(v, date):
        return v

    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None

    # 자동차 파일: "26/01/03"
    if re.match(r"^\d{2}/\d{2}/\d{2}$", s):
        try:
            return datetime.strptime(s, "%y/%m/%d").date()
        except Exception:
            return None

    # "20260103"
    if re.match(r"^\d{8}$", s):
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except Exception:
            return None

    try:
        dt = pd.to_datetime(s, errors="coerce")
        return None if pd.isna(dt) else dt.date()
    except Exception:
        return None


def _to_str_emp_id(v) -> Optional[str]:
    if pd.isna(v) or v == "":
        return None
    try:
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        s = str(v).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s
    except Exception:
        return str(v).strip()


def _to_int_money(v) -> Optional[int]:
    if pd.isna(v) or v == "":
        return None
    try:
        s = str(v).strip().replace(",", "")
        if s == "" or s.lower() == "nan":
            return None
        return int(float(s))
    except Exception:
        return None


def _to_policy_no(v) -> Optional[str]:
    if pd.isna(v) or v == "":
        return None
    s = str(v).strip().replace(" ", "")
    if not s or s.lower() == "nan":
        return None

    m = re.match(r"^(\d+)\.0+$", s)
    if m:
        return m.group(1)

    m2 = re.match(r"^(\d+)\.(\d+)$", s)
    if m2 and set(m2.group(2)) <= {"0"}:
        return m2.group(1)

    return s


def _life_nl_from_insurer(insurer: str) -> str:
    insurer = (insurer or "").strip()
    return "생보" if insurer in LIFE_INSURERS else "손보"


def _parse_ins_period(v) -> Tuple[Optional[date], Optional[date]]:
    if pd.isna(v) or v == "":
        return (None, None)
    s = str(v).strip()
    if "~" not in s:
        return (None, None)
    a, b = [x.strip() for x in s.split("~", 1)]
    ds = de = None
    try:
        ds = datetime.strptime(a, "%Y%m%d").date() if len(a) == 8 else None
    except Exception:
        ds = None
    try:
        de = datetime.strptime(b, "%Y%m%d").date() if len(b) == 8 else None
    except Exception:
        de = None
    return (ds, de)


# -----------------------------
# 업로드 API
# -----------------------------
@grade_required(["superuser"])
@require_POST
def upload_sales_excel(request):
    f = request.FILES.get("excel_file")
    if not f:
        return _json_err("엑셀 파일(excel_file)이 없습니다.", 400)

    try:
        df = pd.read_excel(f)
        df = _normalize_columns(df)
    except Exception as e:
        logger.exception("dash upload read_excel failed")
        return _json_err(f"엑셀 읽기 실패: {e}", 400)

    is_auto = _is_auto_excel(df)
    required = AUTO_REQUIRED_COLS if is_auto else REQUIRED_COLS

    missing = [c for c in required if c not in df.columns]
    if missing:
        tag = "[자동차]" if is_auto else "[일반]"
        return _json_err(f"{tag} 필수 컬럼이 없습니다: {missing}", 400)

    df = df[~df["증권번호"].isna()].copy()

    created_users = updated_users = upserted_rows = skipped_rows = 0
    first_row_error = None

    try:
        with transaction.atomic():
            for idx, r in df.iterrows():
                try:
                    policy_no = _to_policy_no(r.get("증권번호"))
                    insurer = (str(r.get("보험사")).strip() if not pd.isna(r.get("보험사")) else "")

                    if not policy_no or not insurer:
                        skipped_rows += 1
                        continue

                    rd = _to_date(r.get("영수일자"))
                    ym = rd.strftime("%Y-%m") if rd else datetime.now().strftime("%Y-%m")

                    if is_auto:
                        emp_id = _to_str_emp_id(r.get("담당자코드"))
                        name = (str(r.get("담당자명")).strip() if not pd.isna(r.get("담당자명")) else None)
                        part = (str(r.get("소속")).strip() if not pd.isna(r.get("소속")) else None)
                        branch = (str(r.get("파트너")).strip() if not pd.isna(r.get("파트너")) else None)

                        if not emp_id:
                            skipped_rows += 1
                            continue

                        user_defaults = {}
                        if name:
                            user_defaults["name"] = name
                        if part:
                            user_defaults["part"] = part
                        if branch:
                            user_defaults["branch"] = branch

                        user, created = CustomUser.objects.update_or_create(id=emp_id, defaults=user_defaults)
                        created_users += int(created)
                        updated_users += int(not created)

                        ins_start, ins_end = _parse_ins_period(r.get("보험기간"))

                        liability = _to_int_money(r.get("책임"))
                        optional = _to_int_money(r.get("임의"))
                        total = _to_int_money(r.get("합계"))
                        status = (str(r.get("상태")).strip() if not pd.isna(r.get("상태")) else None)
                        vehicle_no = (str(r.get("차량번호")).strip() if not pd.isna(r.get("차량번호")) else None)

                        SalesRecord.objects.update_or_create(
                            policy_no=policy_no,
                            defaults={
                                "user": user,
                                "part_snapshot": part,
                                "branch_snapshot": branch,
                                "name_snapshot": name,
                                "emp_id_snapshot": emp_id,

                                "insurer": insurer,
                                "contractor": None,
                                "insured": (str(r.get("피보험자명")).strip() if not pd.isna(r.get("피보험자명")) else None),

                                "vehicle_no": vehicle_no,
                                "ins_start": ins_start,
                                "ins_end": ins_end,
                                "pay_method": (str(r.get("납입방법")).strip() if not pd.isna(r.get("납입방법")) else None),

                                "receipt_date": rd,
                                "receipt_amount": total,

                                "car_liability": liability,
                                "car_optional": optional,
                                "status": status,

                                "product_code": None,
                                "product_name": None,

                                "life_nl": "자동차",
                                "ym": ym,
                            },
                        )
                        upserted_rows += 1

                    else:
                        emp_id = _to_str_emp_id(r.get("설계사CD"))
                        name = (str(r.get("설계사")).strip() if not pd.isna(r.get("설계사")) else None)
                        part = (str(r.get("소속")).strip() if not pd.isna(r.get("소속")) else None)
                        branch = (str(r.get("영업가족")).strip() if not pd.isna(r.get("영업가족")) else None)

                        if not emp_id:
                            skipped_rows += 1
                            continue

                        user_defaults = {}
                        if name:
                            user_defaults["name"] = name
                        if part:
                            user_defaults["part"] = part
                        if branch:
                            user_defaults["branch"] = branch

                        user, created = CustomUser.objects.update_or_create(id=emp_id, defaults=user_defaults)
                        created_users += int(created)
                        updated_users += int(not created)

                        receipt_amount = _to_int_money(r.get("영수금"))

                        SalesRecord.objects.update_or_create(
                            policy_no=policy_no,
                            defaults={
                                "user": user,
                                "part_snapshot": part,
                                "branch_snapshot": branch,
                                "name_snapshot": name,
                                "emp_id_snapshot": emp_id,

                                "insurer": insurer,
                                "contractor": (str(r.get("계약자")).strip() if not pd.isna(r.get("계약자")) else None),
                                "insured": (str(r.get("주피")).strip() if not pd.isna(r.get("주피")) else None),

                                "ins_start": _to_date(r.get("보험시작")),
                                "ins_end": _to_date(r.get("보험종기")),
                                "pay_method": (str(r.get("납입방법")).strip() if not pd.isna(r.get("납입방법")) else None),

                                "receipt_date": rd,
                                "receipt_amount": receipt_amount,

                                "product_code": (str(r.get("보험사 상품코드")).strip() if not pd.isna(r.get("보험사 상품코드")) else None),
                                "product_name": (str(r.get("보험사 상품명")).strip() if not pd.isna(r.get("보험사 상품명")) else None),

                                "vehicle_no": None,
                                "car_liability": None,
                                "car_optional": None,
                                "status": (str(r.get("상태")).strip() if ("상태" in df.columns and not pd.isna(r.get("상태"))) else None),

                                "life_nl": _life_nl_from_insurer(insurer),
                                "ym": ym,
                            },
                        )
                        upserted_rows += 1

                except Exception as row_e:
                    skipped_rows += 1
                    if first_row_error is None:
                        first_row_error = f"row={idx} policy_no={r.get('증권번호')} err={row_e}"
                    logger.exception("dash upload row failed: idx=%s", idx)

        return JsonResponse(
            {
                "ok": True,
                "message": "업로드 완료",
                "summary": {
                    "detected_type": "auto" if is_auto else "default",
                    "users_created": created_users,
                    "users_updated": updated_users,
                    "rows_upserted": upserted_rows,
                    "rows_skipped": skipped_rows,
                    "rows_in_file": int(len(df)),
                    "first_row_error": first_row_error,
                },
            }
        )

    except Exception as e:
        # ✅ 여기서부터가 “진짜 500 원인”을 잡는 핵심
        logger.exception("dash upload failed (500)")
        return _json_err(f"서버 오류(업로드 처리 중): {e}", 500)
