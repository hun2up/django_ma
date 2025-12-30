# django_ma/commission/views.py

import pandas as pd

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

from accounts.decorators import grade_required
from accounts.models import CustomUser

from .models import DepositSummary, DepositUploadLog


# =========================================================
# Constants
# =========================================================
UPLOAD_CATEGORIES = [
    "최종지급액",
    "환수지급예상",
    "보증증액",
    "보증보험",
    "기타채권",
    "통산생보",
    "통산손보",
    "응당생보",
    "응당손보",
]

SUPPORTED_UPLOAD_TYPES = {"최종지급액"}


# =========================================================
# Utilities
# =========================================================
def _fmt_date(d):
    return d.strftime("%Y-%m-%d") if d else "-"


def _find_first_field(model_obj, candidates=(), keywords=()):
    field_names = [f.name for f in model_obj._meta.fields]
    for c in candidates:
        if c in field_names:
            return c
    for fn in field_names:
        fn_low = fn.lower()
        for kw in keywords:
            if kw in fn_low:
                return fn
    return None


def _build_user_display(u: CustomUser):
    join_field = _find_first_field(
        u,
        candidates=("join_date", "enter_date", "hire_date", "entered_at", "joined_at"),
        keywords=("join", "enter", "hire"),
    )
    retire_field = _find_first_field(
        u,
        candidates=("retire_date", "quit_date", "leave_date", "resigned_at", "retired_at"),
        keywords=("retire", "quit", "leave", "resign"),
    )

    join_value = getattr(u, join_field, None) if join_field else None
    retire_value = getattr(u, retire_field, None) if retire_field else None

    return {
        "id": str(u.pk),
        "name": getattr(u, "name", "") or getattr(u, "username", "") or "",
        "branch": getattr(u, "branch", "") or "-",
        "part": getattr(u, "part", "") or "-",
        "join_date_display": _fmt_date(join_value),
        "retire_date_display": _fmt_date(retire_value) if retire_value else "재직중",
    }


def _get_all_parts():
    return list(
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )


def _json_error(message, status=400, **extra):
    payload = {"ok": False, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _json_ok(message=None, **extra):
    payload = {"ok": True}
    if message is not None:
        payload["message"] = message
    payload.update(extra)
    return JsonResponse(payload)


def _to_int(v, default=0):
    try:
        if v is None:
            return default
        s = str(v).strip().replace(",", "")
        if s.lower() in ("", "nan", "none"):
            return default
        return int(float(s))
    except Exception:
        return default


def _detect_col(df, must_include=(), any_include=()):
    """
    컬럼명 자동탐지:
    - must_include: 모두 포함되어야 함
    - any_include: 하나라도 포함되면 OK
    """
    cols = list(df.columns)
    for c in cols:
        name = str(c).replace(" ", "")
        low = name.lower()
        ok_must = all(k.replace(" ", "").lower() in low for k in must_include)
        ok_any = (not any_include) or any(k.replace(" ", "").lower() in low for k in any_include)
        if ok_must and ok_any:
            return c
    return None


# =========================================================
# Pages (✅ urls.py에서 참조하는 뷰들 포함!)
# =========================================================
@grade_required(["superuser"])
def redirect_to_deposit(request):
    return redirect("commission:deposit_home")


@grade_required(["superuser"])
def deposit_home(request):
    user_id = (request.GET.get("user") or "").strip()

    parts = _get_all_parts()
    categories = UPLOAD_CATEGORIES[:]

    # ✅ 업로드 로그 -> {upload_type: {part: 'YYYY-MM-DD'}}
    upload_logs = DepositUploadLog.objects.all()
    upload_dates = {}
    for log in upload_logs:
        upload_dates.setdefault(log.upload_type, {})
        upload_dates[log.upload_type][log.part] = _fmt_date(log.uploaded_at)

    context = {
        "target": None,
        "payment": None,
        "debt_total": None, 
        "parts": parts,
        "categories": categories,
        "upload_dates": upload_dates,
    }

    if user_id:
        try:
            target = CustomUser.objects.get(pk=user_id)
            display = _build_user_display(target)

            target.join_date_display = display["join_date_display"]
            target.retire_date_display = display["retire_date_display"]

            summary = DepositSummary.objects.filter(user_id=user_id).first()
            context.update(
                {
                    "target": target,
                    "payment": summary.final_payment if summary else None,
                    "debt_total": summary.debt_total if summary else None,
                }
            )
        except CustomUser.DoesNotExist:
            pass

    return render(request, "commission/deposit_home.html", context)


@grade_required(["superuser"])
def support_home(request):
    # ✅ 기존 urls.py와 호환되게 유지
    return render(request, "commission/support_home.html")


@grade_required(["superuser"])
def approval_home(request):
    # ✅ 기존 urls.py와 호환되게 유지
    return render(request, "commission/approval_home.html")


# =========================================================
# APIs
# =========================================================
@grade_required(["superuser"])
def search_user(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})

    qs = (
        CustomUser.objects.filter(Q(id__icontains=q) | Q(name__icontains=q))
        .order_by("id")[:50]
    )
    results = [
        {
            "id": str(u.pk),
            "name": getattr(u, "name", "") or "-",
            "branch": getattr(u, "branch", "") or "-",
            "part": getattr(u, "part", "") or "-",
        }
        for u in qs
    ]
    return JsonResponse({"results": results})


@grade_required(["superuser"])
@login_required
def api_user_detail(request):
    user_id = (request.GET.get("user") or request.GET.get("id") or "").strip()
    if not user_id:
        return _json_error("missing user id", status=400)

    try:
        u = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return _json_error("user not found", status=404)

    return _json_ok(user=_build_user_display(u))


def _norm_emp_id(v):
    """
    사번 정규화:
    - 2542859.0 같은 엑셀 숫자 → "2542859"
    - 공백/NaN 제거
    - 문자열로 통일 (CustomUser PK 타입이 CharField여도 안전)
    """
    if v is None:
        return ""
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none"):
        return ""
    # "2542859.0" -> "2542859"
    if s.endswith(".0"):
        s = s[:-2]
    return s


@csrf_exempt
@grade_required(["superuser"])
def upload_excel(request):
    """
    ✅ 요구사항(최종지급액 업로드)
    - 사번 -> DepositSummary.user_id 매칭
    - 최종지급액 -> DepositSummary.final_payment 삽입
    - 보증채권합계 -> DepositSummary.debt_total 삽입(요청대로 '채권합계' 저장)
    - 업로드 로그(part+upload_type) 업데이트 -> 화면에 업로드일 표시
    """
    if request.method != "POST":
        return _json_error("잘못된 요청 방식입니다.", status=405)

    part = (request.POST.get("part") or "").strip()
    upload_type = (request.POST.get("upload_type") or "").strip()
    excel_file = request.FILES.get("excel_file")

    if not part:
        return _json_error("부서를 선택해주세요.", status=400)
    if upload_type not in SUPPORTED_UPLOAD_TYPES:
        return _json_error("현재는 [최종지급액] 업로드만 지원됩니다.", status=400)
    if not excel_file:
        return _json_error("엑셀 파일이 전달되지 않았습니다.", status=400)

    fs = FileSystemStorage()
    filename = fs.save(excel_file.name, excel_file)
    file_path = fs.path(filename)

    try:
        df = pd.read_excel(file_path, header=0)

        col_user = _detect_col(df, must_include=("사번",))
        col_payment = _detect_col(df, must_include=("최종", "지급"))
        col_debt_total = _detect_col(df, must_include=("보증", "채권", "합계"))

        if not col_user or not col_payment or not col_debt_total:
            return _json_error(...)

        df2 = df[[col_user, col_payment, col_debt_total]].copy()
        df2.columns = ["user_id", "final_payment", "debt_total"]

        # ✅ 사번을 "문자열"로 정규화 (int 강제변환 제거)
        df2["user_id"] = df2["user_id"].apply(_norm_emp_id)
        df2 = df2[df2["user_id"].astype(str).str.len() > 0].copy()

        df2["final_payment"] = df2["final_payment"].apply(_to_int)
        df2["debt_total"] = df2["debt_total"].apply(_to_int)

        # ✅ 존재 유저 조회 (pk 타입 상관없이 안전)
        ids = df2["user_id"].tolist()
        existing_ids = set(
            CustomUser.objects.filter(pk__in=ids).values_list("pk", flat=True)
        )

        # ✅ (원인확정용) 존재/미존재 샘플
        missing_sample = [x for x in ids if x not in existing_ids][:10]

        count = 0
        missing_users = 0

        with transaction.atomic():
            for _, r in df2.iterrows():
                uid = r["user_id"]
                if uid not in existing_ids:
                    missing_users += 1
                    continue

                DepositSummary.objects.update_or_create(
                    user_id=uid,
                    defaults={
                        "final_payment": int(r["final_payment"]),
                        "debt_total": int(r["debt_total"]),
                    },
                )
                count += 1

            now = timezone.now()
            DepositUploadLog.objects.update_or_create(
                part=part,
                upload_type=upload_type,
                defaults={
                    "row_count": count,
                    "file_name": excel_file.name,
                    "uploaded_at": now,
                },
            )

        return _json_ok(
            f"✅ {count}건 업로드 완료 (deposit_summary 반영)",
            uploaded=count,
            missing_users=missing_users,
            existing_users=len(existing_ids),
            missing_sample=missing_sample,   # ✅ 여기 보이면 바로 원인 확정
            part=part,
            upload_type=upload_type,
            uploaded_date=_fmt_date(timezone.now()),
        )

    except Exception as e:
        return _json_error(f"⚠️ 업로드 실패: {str(e)}", status=500)

    finally:
        try:
            fs.delete(filename)
        except Exception:
            pass



@grade_required(["superuser"])
@login_required
def api_deposit_summary(request):
    user_id = (request.GET.get("user") or request.GET.get("id") or "").strip()
    if not user_id:
        return _json_error("missing user id", status=400)

    # user 존재 확인(원하면 생략 가능)
    if not CustomUser.objects.filter(pk=user_id).exists():
        return _json_error("user not found", status=404)

    s = DepositSummary.objects.filter(user_id=user_id).first()
    if not s:
        # 요약행이 없으면 0/None 처리
        return _json_ok(summary={
            "final_payment": 0,
            "debt_total": 0,
            "has_summary": False,
        })

    return _json_ok(summary={
        "final_payment": int(s.final_payment or 0),
        "debt_total": int(s.debt_total or 0),
        "has_summary": True,
    })
