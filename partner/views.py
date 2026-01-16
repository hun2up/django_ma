# django_ma/partner/views.py
# ------------------------------------------------------------
# ✅ Final Refactor + Efficiency Confirm Group(Accordion) extension
# - Structure / Rate / Efficiency 공용 패턴 정리
# - ✅ Efficiency: confirm_group(Accordion) + attachment(FK) 확장
# - ✅ grouped=1 지원(fetch에서 groups + rows 동시 응답 가능)
# - ✅ 처리일자(process_date) 공용 업데이트 함수 안전화(권한/지점 체크 포함)
# - ✅ Legacy alias(ajax_* / api/*) 유지
# ------------------------------------------------------------

import io
import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import (
    EfficiencyChange,
    EfficiencyConfirmAttachment,
    EfficiencyConfirmGroup,
    PartnerChangeLog,
    RateChange,
    RateTable,
    StructureChange,
    SubAdminTemp,
    TableSetting,
)

# ------------------------------------------------------------
# ✅ 공용 상수
# ------------------------------------------------------------
BRANCH_PARTS: Dict[str, list] = {
    "MA사업1부": [],
    "MA사업2부": [],
    "MA사업3부": [],
    "MA사업4부": [],
    "MA사업5부": [],
}

# ------------------------------------------------------------
# ✅ 공용 응답/파서
# ------------------------------------------------------------
def json_ok(payload: Optional[Dict[str, Any]] = None, *, status: int = 200) -> JsonResponse:
    data: Dict[str, Any] = {"status": "success"}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def json_err(message: str, *, status: int = 400, extra: Optional[Dict[str, Any]] = None) -> JsonResponse:
    data: Dict[str, Any] = {"status": "error", "message": message}
    if extra:
        data.update(extra)
    return JsonResponse(data, status=status)


def parse_json_body(request) -> Dict[str, Any]:
    try:
        raw = request.body or b"{}"
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw or "{}")
    except Exception:
        return {}


# ------------------------------------------------------------
# ✅ 공용 유틸
# ------------------------------------------------------------
def get_now_ym() -> Tuple[int, int]:
    now = timezone.localtime(timezone.now())
    return now.year, now.month


def normalize_month(month: str) -> str:
    month = (month or "").strip()
    if not month:
        return ""
    if "-" in month:
        try:
            y, m = month.split("-")
            return f"{y}-{int(m):02d}"
        except Exception:
            return month
    digits = "".join([c for c in month if c.isdigit()])
    if len(digits) == 6:
        return f"{digits[:4]}-{digits[4:6]}"
    return month


def parse_yyyy_mm_dd_or_none(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return datetime.strptime(v, "%Y-%m-%d").date()


def build_current_user_payload(user: CustomUser) -> Dict[str, Any]:
    return {
        "grade": getattr(user, "grade", "") or "",
        "branch": getattr(user, "branch", "") or "",
        "part": getattr(user, "part", "") or "",
        "id": getattr(user, "id", "") or "",
        "name": getattr(user, "name", "") or "",
    }


def resolve_branch_for_query(user: CustomUser, branch_param: str) -> str:
    branch_param = (branch_param or "").strip()
    if getattr(user, "grade", "") == "superuser":
        return branch_param
    return (getattr(user, "branch", "") or "").strip()


def resolve_branch_for_write(user: CustomUser, branch_payload: str) -> str:
    branch_payload = (branch_payload or "").strip()
    if getattr(user, "grade", "") == "superuser":
        return branch_payload or "-"
    return (getattr(user, "branch", "") or branch_payload or "-").strip()


def resolve_part_for_write(user: CustomUser, part_payload: str) -> str:
    part_payload = (part_payload or "").strip()
    return part_payload or (getattr(user, "part", "") or "-").strip()


def _clean_dash(v: str) -> str:
    v = (v or "").strip()
    return "" if v == "-" else v


def build_affiliation_display(user: CustomUser) -> str:
    """
    ✅ 기존 소속 표기(팀A/B/C 중 유효값만 노출)
    - 팀A가 없으면 branch만
    - 팀A/B/C 있으면 "team_a team_b team_c"
    """
    branch = _clean_dash(getattr(user, "branch", "")) or "-"
    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return branch

    team_a = _clean_dash(getattr(sa, "team_a", ""))
    team_b = _clean_dash(getattr(sa, "team_b", ""))
    team_c = _clean_dash(getattr(sa, "team_c", ""))

    if not team_a:
        return branch

    parts = [p for p in [team_a, team_b, team_c] if p]
    return " ".join(parts) if parts else branch


def build_requester_affiliation_chain(user: CustomUser) -> str:
    """
    ✅ 요청자 소속 표기(지점 + 팀A + 팀B + 팀C)
    - 팀A 없으면 지점까지만
    - "-" / 빈값은 제외
    """
    def _clean(v: str) -> str:
        v = (v or "").strip()
        return "" if (not v or v == "-") else v

    branch = _clean(getattr(user, "branch", "")) or "-"
    parts = [branch]

    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return " ".join([p for p in parts if p])

    team_a = _clean(getattr(sa, "team_a", ""))
    team_b = _clean(getattr(sa, "team_b", ""))
    team_c = _clean(getattr(sa, "team_c", ""))

    if team_a:
        parts.append(team_a)
    if team_b:
        parts.append(team_b)
    if team_c:
        parts.append(team_c)

    return " ".join([p for p in parts if p])


def find_table_rate(branch: str, table_name: str) -> str:
    table_name = (table_name or "").strip()
    if not table_name:
        return ""
    ts = TableSetting.objects.filter(branch=branch, table_name=table_name).order_by("order").first()
    return (ts.rate or "") if ts else ""


def _find_part_by_branch(branch: str) -> str:
    b = (branch or "").strip()
    if not b:
        return ""

    p = (
        CustomUser.objects.filter(branch__iexact=b)
        .exclude(part__isnull=True)
        .exclude(part__exact="")
        .values_list("part", flat=True)
        .first()
    )
    if p:
        return str(p).strip()

    for part, branches in BRANCH_PARTS.items():
        if b in (branches or []):
            return part
    return ""


# ------------------------------------------------------------
# ✅ sub_admin 레벨별 팀 필터: requester_id 허용 목록
# ------------------------------------------------------------
def _get_level_team_filter_user_ids(user: CustomUser) -> List[str]:
    """
    ✅ sub_admin 레벨별 팀 필터에 해당하는 '작성자(requester)' user_id 목록 반환
    - A레벨: team_a 동일
    - B레벨: team_b 동일
    - C레벨: team_c 동일
    - 레벨/팀값 없으면 빈 리스트
    """
    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return []

    level = (sa.level or "").strip()
    if level not in ["A레벨", "B레벨", "C레벨"]:
        return []

    field = {"A레벨": "team_a", "B레벨": "team_b", "C레벨": "team_c"}[level]
    my_team_value = _clean_dash(getattr(sa, field, "") or "")
    if not my_team_value:
        return []

    return list(
        SubAdminTemp.objects.filter(
            branch=(user.branch or "").strip(),
            **{f"{field}__iexact": my_team_value},
        ).values_list("user_id", flat=True)
    )


# ------------------------------------------------------------
# ✅ confirm_group_id 생성(업로드 성공 시점)
# 형식: YYYYMMDDHHMM_사번_순번(2자리)
# ------------------------------------------------------------
def _generate_confirm_group_id(*, uploader_id: str) -> str:
    now = timezone.localtime(timezone.now())
    prefix = now.strftime("%Y%m%d%H%M")  # 분 단위
    base = f"{prefix}_{uploader_id}_"

    same_minute_qs = EfficiencyConfirmGroup.objects.select_for_update().filter(confirm_group_id__startswith=base)
    cnt = same_minute_qs.count()
    seq = min(cnt + 1, 99)  # 현실적으로 99 초과는 거의 없다고 가정
    return f"{base}{seq:02d}"


# ------------------------------------------------------------
# ✅ 페이지 공용 컨텍스트 빌더
# ------------------------------------------------------------
def build_manage_context(
    *,
    request,
    page_kind: str,
    template_name: str,
    fetch_name: str,
    save_name: str,
    delete_name: str,
    update_process_name: str,
    boot_key: str,
    extra_context: Optional[Dict[str, Any]] = None,
):
    y, m = get_now_ym()
    user = request.user

    data_fetch_url = reverse(fetch_name)
    data_save_url = reverse(save_name)
    data_delete_url = reverse(delete_name)
    update_process_date_url = reverse(update_process_name)

    boot = {
        "userGrade": getattr(user, "grade", ""),
        "currentYear": y,
        "currentMonth": m,
        "selectedYear": y,
        "selectedMonth": m,
        "autoLoad": getattr(user, "grade", "") in ["main_admin", "sub_admin"],
        "dataFetchUrl": data_fetch_url,
        "dataSaveUrl": data_save_url,
        "dataDeleteUrl": data_delete_url,
        "updateProcessDateUrl": update_process_date_url,
        "kind": page_kind,
    }

    ctx: Dict[str, Any] = {
        "current_year": y,
        "current_month": m,
        "selected_year": y,
        "selected_month": m,
        "auto_load": True,
        "data_fetch_url": data_fetch_url,
        "data_save_url": data_save_url,
        "data_delete_url": data_delete_url,
        "update_process_date_url": update_process_date_url,
        boot_key: boot,
        "currentUser": build_current_user_payload(user),
    }
    if extra_context:
        ctx.update(extra_context)
    return render(request, template_name, ctx)


# ------------------------------------------------------------
# ✅ 지점효율 확인서 양식 다운로드
# ------------------------------------------------------------
@login_required
def efficiency_confirm_template_download(request):
    rel_path = "excel/양식_지점효율확인서.xlsx"
    abs_path = finders.find(rel_path)
    if not abs_path:
        raise Http404("양식 파일을 찾을 수 없습니다.")
    try:
        f = open(abs_path, "rb")
    except OSError:
        raise Http404("양식 파일을 열 수 없습니다.")
    return FileResponse(
        f,
        as_attachment=True,
        filename="양식_지점효율확인서.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------
@grade_required(["superuser", "main_admin", "sub_admin"])
def redirect_to_calculate(request):
    return redirect("partner:manage_calculate")


@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_calculate(request):
    return build_manage_context(
        request=request,
        page_kind="efficiency",
        template_name="partner/manage_calculate.html",
        fetch_name="partner:efficiency_fetch",
        save_name="partner:efficiency_save",
        delete_name="partner:efficiency_delete_row",
        update_process_name="partner:efficiency_update_process_date",
        boot_key="ManageefficiencyBoot",
        extra_context={
            "search_user_url": "/api/accounts/search-user/",
            "efficiency_confirm_groups_url": reverse("partner:efficiency_confirm_groups"),
        },
    )


@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_rate(request):
    user = request.user
    subadmin_info = SubAdminTemp.objects.filter(user=user).first()
    return build_manage_context(
        request=request,
        page_kind="rate",
        template_name="partner/manage_rate.html",
        fetch_name="partner:rate_fetch",
        save_name="partner:rate_save",
        delete_name="partner:rate_delete",
        update_process_name="partner:rate_update_process_date",
        boot_key="ManageRateBoot",
        extra_context={"subadmin_info": subadmin_info},
    )


@grade_required(["superuser", "main_admin"])
def manage_tables(request):
    return render(request, "partner/manage_tables.html")


@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_charts(request):
    user = request.user
    subadmin_info = SubAdminTemp.objects.filter(user=user).first()
    selected_branch = user.branch if getattr(user, "grade", "") == "main_admin" and user.branch else None

    return build_manage_context(
        request=request,
        page_kind="structure",
        template_name="partner/manage_charts.html",
        fetch_name="partner:structure_fetch",
        save_name="partner:structure_save",
        delete_name="partner:structure_delete",
        update_process_name="partner:structure_update_process_date",
        boot_key="ManageStructureBoot",
        extra_context={
            "branches": sorted(list(BRANCH_PARTS.keys())),
            "selected_branch": selected_branch,
            "subadmin_info": subadmin_info,
        },
    )


# ------------------------------------------------------------
# ✅ 처리일자(process_date) 공용 업데이트
# - record 조회 이전에 branch 체크하면 안 되므로, record 먼저 로드 후 검사
# - main_admin: 자기 지점만 수정 가능
# ------------------------------------------------------------
def _resolve_process_model(kind: str) -> Optional[Type]:
    k = (kind or "").strip().lower()
    if k == "structure":
        return StructureChange
    if k == "rate":
        return RateChange
    if k == "efficiency":
        return EfficiencyChange
    return None


def _update_process_date_common(*, request, kind: str, record_id, new_date: str) -> JsonResponse:
    if not record_id:
        return json_err("id 누락", status=400)

    model = _resolve_process_model(kind)
    if model is None:
        return json_err(f"지원하지 않는 kind: {kind}", status=400)

    record = get_object_or_404(model, id=record_id)

    # ✅ main_admin 지점 제한
    if request.user.grade == "main_admin":
        rec_branch = (getattr(record, "branch", "") or "").strip()
        my_branch = (request.user.branch or "").strip()
        if rec_branch and my_branch and rec_branch != my_branch:
            return json_err("다른 지점 데이터의 처리일자는 수정할 수 없습니다.", status=403)

    # 날짜 파싱
    if (new_date or "") == "":
        parsed_date = None
    else:
        try:
            parsed_date = parse_yyyy_mm_dd_or_none(new_date)
        except ValueError:
            return json_err("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)", status=400)

    record.process_date = parsed_date
    record.save(update_fields=["process_date"])

    PartnerChangeLog.objects.create(
        user=request.user,
        action="update_process_date",
        detail=f"[{kind}] ID {record_id} 처리일자 수정 → {new_date or 'NULL'}",
    )
    return json_ok({"message": "처리일자 변경 완료", "process_date": new_date})


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def structure_update_process_date(request):
    payload = parse_json_body(request)
    return _update_process_date_common(
        request=request,
        kind="structure",
        record_id=payload.get("id"),
        new_date=(payload.get("process_date") or "").strip(),
    )


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def rate_update_process_date(request):
    payload = parse_json_body(request)
    return _update_process_date_common(
        request=request,
        kind="rate",
        record_id=payload.get("id"),
        new_date=(payload.get("process_date") or "").strip(),
    )


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def efficiency_update_process_date(request):
    payload = parse_json_body(request)
    return _update_process_date_common(
        request=request,
        kind="efficiency",
        record_id=payload.get("id"),
        new_date=(payload.get("process_date") or "").strip(),
    )


# ------------------------------------------------------------
# Structure - core (ajax_*) + aliases
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_save(request):
    try:
        payload = parse_json_body(request)
        items = payload.get("rows", [])
        month = normalize_month(payload.get("month") or "")

        user = request.user
        part = resolve_part_for_write(user, payload.get("part") or "")
        branch = resolve_branch_for_write(user, payload.get("branch") or "")

        created_count = 0
        for row in items:
            target_id = str(row.get("target_id") or "").strip()
            if not target_id:
                continue
            target = CustomUser.objects.filter(id=target_id).first()
            if not target:
                continue

            StructureChange.objects.create(
                requester=user,
                target=target,
                part=part,
                branch=branch,
                month=month,
                target_branch=build_affiliation_display(target),
                chg_branch=(row.get("chg_branch") or "-").strip() or "-",
                or_flag=bool(row.get("or_flag", False)),
                rank=(row.get("tg_rank") or row.get("rank") or "-").strip() or "-",
                chg_rank=(row.get("chg_rank") or "-").strip() or "-",
                memo=(row.get("memo") or "").strip(),
            )
            created_count += 1

        PartnerChangeLog.objects.create(
            user=user,
            action="save",
            detail=f"{created_count}건 저장 (structure / 월:{month} / 부서:{part} / 지점:{branch})",
        )
        return json_ok({"saved_count": created_count})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=400)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_delete(request):
    try:
        data = parse_json_body(request)
        record_id = data.get("id")
        if not record_id:
            return json_err("id 누락", status=400)

        record = get_object_or_404(StructureChange, id=record_id)
        user = request.user

        if not (user.grade in ["superuser", "main_admin"] or record.requester_id == user.id):
            return json_err("삭제 권한이 없습니다.", status=403)

        deleted_id = record.id
        record.delete()

        PartnerChangeLog.objects.create(user=user, action="delete", detail=f"StructureChange #{deleted_id} 삭제")
        return json_ok({"message": f"#{deleted_id} 삭제 완료"})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_fetch(request):
    """
    ✅ Structure 조회
    - superuser: 선택 branch(있으면) / 없으면 전체
    - main_admin: 자기 지점
    - sub_admin: 자기 작성 + 레벨팀 동일 작성자(같은 지점) 제한
    """
    try:
        user = request.user
        month = normalize_month(request.GET.get("month") or "")
        branch_param = (request.GET.get("branch") or "").strip()
        branch = resolve_branch_for_query(user, branch_param)

        qs = StructureChange.objects.filter(month=month).select_related("requester", "target")

        if user.grade == "superuser":
            if branch:
                qs = qs.filter(branch__iexact=branch)
        else:
            qs = qs.filter(branch__iexact=branch)

        if user.grade == "sub_admin":
            allowed_ids = _get_level_team_filter_user_ids(user)
            team_q = Q(requester_id__in=allowed_ids) if allowed_ids else Q()
            qs = qs.filter(Q(requester_id=user.id) | team_q)

        rows = []
        for sc in qs.order_by("-id"):
            rows.append(
                {
                    "id": sc.id,
                    "requester_id": getattr(sc.requester, "id", "") if sc.requester else "",
                    "requester_name": getattr(sc.requester, "name", "") if sc.requester else "",
                    "requester_branch": build_affiliation_display(sc.requester) if sc.requester else "",
                    "target_id": getattr(sc.target, "id", "") if sc.target else "",
                    "target_name": getattr(sc.target, "name", "") if sc.target else "",
                    "target_branch": sc.target_branch or "",
                    "chg_branch": sc.chg_branch or "",
                    "rank": sc.rank or "",
                    "chg_rank": sc.chg_rank or "",
                    "or_flag": bool(sc.or_flag),
                    "memo": sc.memo or "",
                    "request_date": sc.created_at.strftime("%Y-%m-%d") if sc.created_at else "",
                    "process_date": sc.process_date.strftime("%Y-%m-%d") if sc.process_date else "",
                }
            )

        return json_ok({"kind": "structure", "rows": rows})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500, extra={"rows": []})


# ------------------------------------------------------------
# Efficiency (지점효율) - fetch + groups payload
# ------------------------------------------------------------
def _build_efficiency_groups_payload(*, month: str, branch: str, user: CustomUser) -> List[Dict[str, Any]]:
    """
    ✅ Accordion 렌더링용 그룹 구조
    - group_key: confirm_group_id(문자열)
    - group_pk: DB PK(숫자)
    - ✅ 권한별 조회범위 적용:
      superuser: 선택 branch 전체
      main_admin: 자기 branch 전체
      sub_admin(A/B/C): 자기 팀 범위(uploader 기준)
    """
    gqs = EfficiencyConfirmGroup.objects.filter(month=month)

    # ✅ branch scope
    if user.grade == "superuser":
        if branch:
            gqs = gqs.filter(branch__iexact=branch)
        else:
            # superuser가 branch 없이 호출하면 빈 리스트로 (프론트 정책과 동일)
            return []
    else:
        gqs = gqs.filter(branch__iexact=branch)

    # ✅ sub_admin: 팀 범위(uploader 기준)
    if user.grade == "sub_admin":
        allowed_ids = _get_level_team_filter_user_ids(user)  # 같은 branch + 같은 level team의 user_id들
        if allowed_ids:
            gqs = gqs.filter(uploader_id__in=allowed_ids)
        else:
            # 레벨/팀 미설정이면 누수 방지: 본인 업로드만
            gqs = gqs.filter(uploader_id=user.id)

    gqs = gqs.annotate(
        row_count=Count("efficiency_rows", distinct=True),
        total_amount=Sum("efficiency_rows__amount"),
    ).order_by("-id")

    groups: List[Dict[str, Any]] = []
    for g in gqs:
        atts = []
        for a in g.attachments.all().order_by("-id"):
            atts.append(
                {
                    "id": a.id,
                    "file_name": a.original_name or (a.file.name.split("/")[-1] if a.file else ""),
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                    "file": a.file.url if getattr(a, "file", None) and hasattr(a.file, "url") else "",
                }
            )

        cg_id = (g.confirm_group_id or "").strip()
        groups.append(
            {
                "confirm_group_id": cg_id,
                "group_key": cg_id,
                "id": g.id,
                "group_pk": g.id,
                "month": g.month,
                "part": g.part,
                "branch": g.branch,
                "title": g.title or "",
                "note": g.note or "",
                "created_at": g.created_at.strftime("%Y-%m-%d %H:%M") if g.created_at else "",
                "row_count": int(getattr(g, "row_count", 0) or 0),
                "total_amount": int(getattr(g, "total_amount", 0) or 0),
                "attachments": atts,
            }
        )
    return groups


@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def efficiency_fetch(request):
    """
    ✅ rows 응답 유지
    ✅ grouped=1이면 groups(Accordion) 같이 내려줌
    ✅ group_key(confirm_group_id) + group_pk 제공(프론트 매칭)
    """
    try:
        user = request.user
        month = normalize_month(request.GET.get("month") or "")
        branch_param = (request.GET.get("branch") or "").strip()
        branch = resolve_branch_for_query(user, branch_param)

        qs = (
            EfficiencyChange.objects.filter(month=month)
            .select_related("requester", "confirm_group")
            .order_by("-id")
        )

        if user.grade == "superuser":
            if branch:
                qs = qs.filter(branch__iexact=branch)
        else:
            qs = qs.filter(branch__iexact=branch)

        # ✅ sub_admin: 팀 범위(requester 기준)
        if user.grade == "sub_admin":
            allowed_ids = _get_level_team_filter_user_ids(user)
            if allowed_ids:
                qs = qs.filter(requester_id__in=allowed_ids)
            else:
                # 레벨/팀 미설정이면 누수 방지: 본인 작성만
                qs = qs.filter(requester_id=user.id)

        rows = []
        for ec in qs:
            amount_val = int(ec.amount or 0)
            tax_val = int(round(amount_val * 0.033)) if amount_val > 0 else 0

            cg = ec.confirm_group
            cg_id = (getattr(cg, "confirm_group_id", "") or "").strip() if cg else ""
            cg_pk = getattr(cg, "id", None) if cg else None

            rows.append(
                {
                    "id": ec.id,
                    "requester_name": getattr(ec.requester, "name", "") if ec.requester else "",
                    "requester_id": getattr(ec.requester, "id", "") if ec.requester else "",
                    "requester_branch": build_affiliation_display(ec.requester) if ec.requester else "",
                    "category": ec.category or "",
                    "amount": amount_val,
                    "tax": tax_val,
                    "ded_name": ec.ded_name or "",
                    "ded_id": ec.ded_id or "",
                    "pay_name": ec.pay_name or "",
                    "pay_id": ec.pay_id or "",
                    "content": ec.content or "",
                    "memo": ec.memo or "",
                    "request_date": ec.created_at.strftime("%Y-%m-%d") if ec.created_at else "",
                    "process_date": ec.process_date.strftime("%Y-%m-%d") if ec.process_date else "",
                    "confirm_group_id": cg_id,
                    "group_key": cg_id,
                    "confirm_group_pk": cg_pk,
                    "group_pk": cg_pk,
                }
            )

        payload: Dict[str, Any] = {"kind": "efficiency", "rows": rows}

        if (request.GET.get("grouped") or "").strip() == "1":
            payload["groups"] = _build_efficiency_groups_payload(month=month, branch=branch, user=user)

        return json_ok(payload)

    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500, extra={"rows": [], "groups": []})


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def efficiency_save(request):
    """
    ✅ Efficiency 저장
    - payload.confirm_group_id 필수
    - EfficiencyChange.confirm_group 연결
    - 저장 시 group.title을 "YYYY-MM-DD / 지점 팀A 팀B 팀C" 로 업데이트
    """
    try:
        payload = parse_json_body(request)
        items = payload.get("rows", [])
        if not isinstance(items, list):
            return json_err("rows 형식이 올바르지 않습니다.", status=400)

        month = normalize_month(payload.get("month") or "")
        if not month:
            return json_err("month(YYYY-MM)가 없습니다.", status=400)

        user = request.user
        part = resolve_part_for_write(user, payload.get("part") or "")
        branch = resolve_branch_for_write(user, payload.get("branch") or "")

        if getattr(user, "grade", "") == "superuser" and not (branch or "").strip():
            return json_err("superuser는 branch가 필요합니다.", status=400)

        confirm_group_id = (payload.get("confirm_group_id") or "").strip()
        if not confirm_group_id:
            return json_err("confirm_group_id가 없습니다. 확인서 업로드 후 저장하세요.", status=400)

        group = (
            EfficiencyConfirmGroup.objects.select_for_update()
            .filter(confirm_group_id=confirm_group_id)
            .first()
        )
        if not group:
            return json_err("confirm_group_id에 해당하는 그룹을 찾을 수 없습니다.", status=404)

        if (group.month or "").strip() != month:
            return json_err("그룹 월도와 저장 월도가 다릅니다.", status=400)

        req_branch = (branch or "").strip()
        group_branch = (group.branch or "").strip()

        if user.grade == "superuser":
            if req_branch and group_branch != req_branch:
                return json_err("그룹 지점과 저장 지점이 다릅니다.", status=400)
        else:
            if group_branch != req_branch:
                return json_err("그룹 지점과 저장 지점이 다릅니다.", status=400)

        # ✅ 그룹 title 업데이트
        save_date = timezone.localdate(timezone.now()).strftime("%Y-%m-%d")
        aff = build_requester_affiliation_chain(user)
        new_title = f"{save_date} / {aff}"
        if (group.title or "").strip() != new_title:
            group.title = new_title
            group.save(update_fields=["title"])

        latest_att = group.attachments.order_by("-id").first()

        objs: List[EfficiencyChange] = []
        skipped = 0

        for row in items:
            if not isinstance(row, dict):
                skipped += 1
                continue

            category = (row.get("category") or "").strip()
            content = (row.get("content") or "").strip()

            try:
                amount = int(row.get("amount", 0))
            except Exception:
                amount = 0

            if not category or not content or amount <= 0:
                skipped += 1
                continue

            ded_id = str(row.get("ded_id") or "").strip()
            ded_name = (row.get("ded_name") or "").strip()
            pay_id = str(row.get("pay_id") or "").strip()
            pay_name = (row.get("pay_name") or "").strip()
            memo = (row.get("memo") or content[:200]).strip()

            objs.append(
                EfficiencyChange(
                    requester=user,
                    part=part,
                    branch=branch,
                    month=month,
                    category=category,
                    amount=amount,
                    ded_id=ded_id,
                    ded_name=ded_name,
                    pay_id=pay_id,
                    pay_name=pay_name,
                    content=content,
                    memo=memo,
                    confirm_group=group,
                    confirm_attachment=latest_att,  # 필요 없으면 모델/프론트에서 제거 가능
                )
            )

        if not objs:
            return json_err("저장할 유효 데이터가 없습니다. (구분/금액/내용 확인)", status=400)

        EfficiencyChange.objects.bulk_create(objs, batch_size=500)

        PartnerChangeLog.objects.create(
            user=user,
            action="save",
            detail=(
                f"{len(objs)}건 저장 (efficiency / 월:{month} / 부서:{part} / 지점:{branch} "
                f"/ group:{group.confirm_group_id} / skipped:{skipped})"
            ),
        )

        return json_ok(
            {
                "saved_count": len(objs),
                "skipped": skipped,
                "confirm_group_id": group.confirm_group_id,
                "group_title": group.title or "",
            }
        )

    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=400)


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def efficiency_delete_row(request):
    """
    ✅ 그룹 내부 행(단건) 삭제
    """
    try:
        payload = parse_json_body(request)
        row_id = payload.get("id")
        if not row_id:
            return json_err("id가 없습니다.", status=400)

        obj = EfficiencyChange.objects.select_for_update().filter(id=row_id).first()
        if not obj:
            return json_err("삭제 대상이 없습니다.", status=404)

        user = request.user
        if user.grade != "superuser":
            if (obj.branch or "") != (getattr(user, "branch", "") or ""):
                return json_err("권한이 없습니다.", status=403)

        obj.delete()

        PartnerChangeLog.objects.create(
            user=user,
            action="delete_row",
            detail=f"efficiency row delete id={row_id}",
        )
        return json_ok()

    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=400)


@require_POST
@login_required
@grade_required(["superuser", "main_admin"])  # ✅ sub_admin 차단
@transaction.atomic
def efficiency_delete_group(request):
    """
    ✅ 그룹 삭제(실제 파일 포함)
    - group_id: confirm_group_id(문자열) 또는 group pk(숫자) 허용
    """
    payload = parse_json_body(request)
    group_id = str(payload.get("group_id") or "").strip()
    if not group_id:
        return json_err("group_id가 없습니다.", status=400)

    group = EfficiencyConfirmGroup.objects.select_for_update().filter(confirm_group_id=group_id).first()
    if group is None and group_id.isdigit():
        group = EfficiencyConfirmGroup.objects.select_for_update().filter(pk=int(group_id)).first()

    if group is None:
        return json_err("그룹을 찾을 수 없습니다.", status=404)

    if request.user.grade == "main_admin":
        rec_branch = (group.branch or "").strip()
        my_branch = (request.user.branch or "").strip()
        if rec_branch and my_branch and rec_branch != my_branch:
            return json_err("다른 지점 그룹은 삭제할 수 없습니다.", status=403)

    try:
        EfficiencyChange.objects.filter(confirm_group=group).delete()

        for att in group.attachments.all():
            if att.file:
                att.file.delete(save=False)
            att.delete()

        group.delete()

        PartnerChangeLog.objects.create(
            user=request.user,
            action="delete_group",
            detail=f"efficiency group delete confirm_group_id={group.confirm_group_id}",
        )
        return json_ok()

    except Exception as e:
        traceback.print_exc()
        return json_err(f"삭제 중 오류: {e}", status=500)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def efficiency_confirm_upload(request):
    """
    ✅ 확인서 업로드
    - confirm_group_id가 없으면 업로드 시점에 그룹 생성
    - 있으면 동일 그룹에 첨부 누적
    """
    f = request.FILES.get("file")
    if not f:
        return json_err("파일이 없습니다.", status=400)

    allowed = (".pdf", ".png", ".jpg", ".jpeg", ".heic", ".xlsx", ".xls")
    name_lower = (f.name or "").lower()
    if allowed and not any(name_lower.endswith(ext) for ext in allowed):
        return json_err("허용되지 않는 파일 형식입니다.", status=400)

    payload_part = (request.POST.get("part") or "").strip()
    payload_branch = (request.POST.get("branch") or "").strip()
    payload_month = normalize_month(request.POST.get("month") or "")
    incoming_group_id = (request.POST.get("confirm_group_id") or "").strip()

    user = request.user
    part = resolve_part_for_write(user, payload_part)
    branch = resolve_branch_for_write(user, payload_branch)

    if not payload_month:
        return json_err("month(YYYY-MM)가 없습니다.", status=400)
    if user.grade == "superuser" and not branch:
        return json_err("superuser는 branch가 필요합니다.", status=400)

    group: Optional[EfficiencyConfirmGroup] = None

    if incoming_group_id:
        group = EfficiencyConfirmGroup.objects.select_for_update().filter(confirm_group_id=incoming_group_id).first()
        if not group:
            return json_err("confirm_group_id에 해당하는 그룹을 찾을 수 없습니다.", status=404)

        if (group.month or "") != payload_month:
            return json_err("그룹 월도와 업로드 월도가 다릅니다.", status=400)

        if user.grade != "superuser":
            if (group.branch or "") != branch:
                return json_err("그룹 지점과 업로드 지점이 다릅니다.", status=400)
        else:
            if branch and (group.branch or "") != branch:
                return json_err("그룹 지점과 업로드 지점이 다릅니다.", status=400)

    else:
        new_group_id = _generate_confirm_group_id(uploader_id=str(getattr(user, "id", "") or ""))
        group = EfficiencyConfirmGroup.objects.create(
            confirm_group_id=new_group_id,
            uploader=user,
            part=part,
            branch=branch,
            month=payload_month,
            title="",
            note="",
        )

    att = EfficiencyConfirmAttachment.objects.create(
        group=group,
        uploader=user,
        part=part,
        branch=branch,
        month=payload_month,
        file=f,
        original_name=f.name or "",
    )

    PartnerChangeLog.objects.create(
        user=user,
        action="confirm_upload",
        detail=(
            f"[efficiency] confirm_group_id={group.confirm_group_id} attachment_id={att.id} "
            f"month={payload_month} branch={branch}"
        ),
    )

    return json_ok(
        {
            "confirm_group_id": group.confirm_group_id,
            "attachment_id": att.id,
            "file_name": att.original_name or (att.file.name.split("/")[-1] if att.file else ""),
            "group_created_at": group.created_at.strftime("%Y-%m-%d %H:%M") if group.created_at else "",
        }
    )


@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def efficiency_confirm_groups(request):
    """
    ✅ Accordion 전용 그룹 목록 API
    """
    try:
        user = request.user
        month = normalize_month(request.GET.get("month") or "")
        branch_param = (request.GET.get("branch") or "").strip()
        branch = resolve_branch_for_query(user, branch_param)

        if not month:
            return json_err("month(YYYY-MM)가 없습니다.", status=400)

        if user.grade == "superuser" and not branch:
            return json_ok({"groups": []})

        groups = _build_efficiency_groups_payload(month=month, branch=branch, user=user)
        return json_ok({"groups": groups})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500, extra={"groups": []})


# ------------------------------------------------------------
# Rate Change
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def rate_fetch(request):
    user = request.user
    month = normalize_month(request.GET.get("month") or "")
    branch_param = (request.GET.get("branch") or "").strip()
    branch = resolve_branch_for_query(user, branch_param)

    qs = RateChange.objects.filter(month=month).select_related("requester", "target")

    if user.grade == "superuser":
        if branch:
            qs = qs.filter(branch__iexact=branch)
    else:
        qs = qs.filter(branch__iexact=branch)

    if user.grade == "sub_admin":
        allowed_ids = _get_level_team_filter_user_ids(user)
        team_q = Q(requester_id__in=allowed_ids) if allowed_ids else Q()
        qs = qs.filter(Q(requester_id=user.id) | team_q)

    qs = qs.order_by("-id")

    rows = []
    for rc in qs:
        rows.append(
            {
                "id": rc.id,
                "requester_name": rc.requester.name,
                "requester_id": rc.requester.id,
                "target_name": rc.target.name,
                "target_id": rc.target.id,
                "before_ftable": rc.before_ftable,
                "before_frate": rc.before_frate,
                "after_ftable": rc.after_ftable,
                "after_frate": rc.after_frate,
                "before_ltable": rc.before_ltable,
                "before_lrate": rc.before_lrate,
                "after_ltable": rc.after_ltable,
                "after_lrate": rc.after_lrate,
                "memo": rc.memo,
                "request_date": rc.created_at.strftime("%Y-%m-%d") if rc.created_at else "",
                "process_date": rc.process_date.strftime("%Y-%m-%d") if rc.process_date else "",
            }
        )

    return json_ok({"kind": "rate", "rows": rows})


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def rate_save(request):
    payload = parse_json_body(request)
    rows = payload.get("rows", [])
    month = normalize_month(payload.get("month") or "")

    user = request.user
    part = resolve_part_for_write(user, payload.get("part") or "")
    branch = resolve_branch_for_write(user, payload.get("branch") or "")

    saved = 0
    for r in rows:
        target_id = str(r.get("target_id") or "").strip()
        if not target_id:
            continue

        target = CustomUser.objects.filter(id=target_id).first()
        if not target:
            continue

        rt = RateTable.objects.filter(user=target).first()
        before_ftable = rt.non_life_table if rt else ""
        before_ltable = rt.life_table if rt else ""

        before_frate = find_table_rate(target.branch, before_ftable)
        before_lrate = find_table_rate(target.branch, before_ltable)

        after_ftable = (r.get("after_ftable") or "").strip()
        after_ltable = (r.get("after_ltable") or "").strip()

        after_frate = find_table_rate(target.branch, after_ftable)
        after_lrate = find_table_rate(target.branch, after_ltable)

        memo = (r.get("memo") or "").strip()

        RateChange.objects.create(
            requester=user,
            target=target,
            part=part,
            branch=branch,
            month=month,
            before_ftable=before_ftable,
            before_frate=before_frate,
            before_ltable=before_ltable,
            before_lrate=before_lrate,
            after_ftable=after_ftable,
            after_frate=after_frate,
            after_ltable=after_ltable,
            after_lrate=after_lrate,
            memo=memo,
        )
        saved += 1

    return json_ok({"saved_count": saved})


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def rate_delete(request):
    data = parse_json_body(request)
    record_id = data.get("id")
    if not record_id:
        return json_err("id 누락", status=400)

    rc = get_object_or_404(RateChange, id=record_id)
    user = request.user

    if not (user.grade in ["superuser", "main_admin"] or rc.requester_id == user.id):
        return json_err("삭제 권한이 없습니다.", status=403)

    rc.delete()
    return json_ok({})


# ------------------------------------------------------------
# Permission Management (manage_grades + excel upload + dt api)
# ------------------------------------------------------------
@grade_required(["superuser", "main_admin"])
def manage_grades(request):
    user = request.user
    LEVELS = ["-", "A레벨", "B레벨", "C레벨"]
    parts = sorted(list(BRANCH_PARTS.keys()))

    selected_part = (request.GET.get("part") or "").strip()
    selected_branch = (request.GET.get("branch") or "").strip()

    base_sub_admin_users = CustomUser.objects.filter(grade="sub_admin")

    if user.grade == "superuser":
        if selected_part and selected_branch:
            subadmin_qs = SubAdminTemp.objects.filter(
                part=selected_part,
                branch=selected_branch,
                user__in=base_sub_admin_users,
            )
            users_all = CustomUser.objects.filter(part=selected_part, branch=selected_branch)
        else:
            subadmin_qs = SubAdminTemp.objects.none()
            users_all = CustomUser.objects.none()
    else:
        selected_branch = (user.branch or "").strip()
        selected_part = _find_part_by_branch(selected_branch) or (user.part or "").strip()

        subadmin_qs = SubAdminTemp.objects.filter(branch=selected_branch, user__in=base_sub_admin_users)
        users_all = CustomUser.objects.filter(branch=selected_branch)

    empty_message_subadmin = "" if subadmin_qs.exists() else "표시할 중간관리자가 없습니다."

    return render(
        request,
        "partner/manage_grades.html",
        {
            "parts": parts,
            "selected_part": selected_part or None,
            "selected_branch": selected_branch or None,
            "users_subadmin": subadmin_qs,
            "users_all": users_all,
            "empty_message_subadmin": empty_message_subadmin,
            "levels": LEVELS,
        },
    )


@transaction.atomic
@grade_required(["superuser", "main_admin"])
def upload_grades_excel(request):
    redirect_part = (request.GET.get("part") or "").strip()
    redirect_branch = (request.GET.get("branch") or "").strip()

    def _redirect():
        qs = []
        if redirect_part:
            qs.append(f"part={redirect_part}")
        if redirect_branch:
            qs.append(f"branch={redirect_branch}")
        base = reverse("partner:manage_grades")
        return redirect(f"{base}?{'&'.join(qs)}" if qs else base)

    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(file, sheet_name="업로드").fillna("")
            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return _redirect()

            for col in ["부서", "지점", "등급"]:
                if col in df.columns:
                    df = df.drop(columns=[col])

            updated, created = 0, 0
            for _, row in df.iterrows():
                user_id = str(row["사번"]).strip()
                cu = CustomUser.objects.filter(id=user_id).first()
                if not cu:
                    continue

                _, is_created = SubAdminTemp.objects.update_or_create(
                    user=cu,
                    defaults={
                        "part": cu.part or "-",
                        "branch": cu.branch or "-",
                        "name": cu.name or "-",
                        "team_a": row["팀A"] or "-",
                        "team_b": row["팀B"] or "-",
                        "team_c": row["팀C"] or "-",
                        "position": row["직급"] or "-",
                    },
                )
                created += 1 if is_created else 0
                updated += 0 if is_created else 1

            messages.success(request, f"업로드 완료: 신규 {created}건, 수정 {updated}건 반영")
        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"엑셀 처리 중 오류 발생: {e}")
    else:
        messages.warning(request, "엑셀 파일을 선택하세요.")

    return _redirect()


@grade_required(["superuser", "main_admin"])
def ajax_users_data(request):
    user = request.user

    try:
        draw = int(request.GET.get("draw", "1") or "1")
    except ValueError:
        draw = 1

    try:
        start = max(int(request.GET.get("start", 0)), 0)
    except ValueError:
        start = 0

    try:
        length = int(request.GET.get("length", 10))
        if length <= 0:
            length = 10
    except ValueError:
        length = 10

    search = (request.GET.get("search[value]", "") or "").strip()
    selected_part = (request.GET.get("part", "") or "").strip()
    selected_branch = (request.GET.get("branch", "") or "").strip()

    try:
        if user.grade == "superuser":
            if not selected_part or not selected_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)
            base_qs = CustomUser.objects.filter(part=selected_part, branch=selected_branch)
        else:
            fixed_branch = (user.branch or "").strip()
            if not fixed_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)
            base_qs = CustomUser.objects.filter(branch=fixed_branch)
            if not selected_part:
                selected_part = _find_part_by_branch(fixed_branch) or (user.part or "").strip()

        records_total = base_qs.count()
        qs = base_qs

        if search:
            ids_from_custom = list(
                qs.filter(
                    Q(name__icontains=search)
                    | Q(id__icontains=search)
                    | Q(branch__icontains=search)
                    | Q(part__icontains=search)
                ).values_list("id", flat=True)
            )
            ids_from_subadmin = list(
                SubAdminTemp.objects.filter(
                    Q(team_a__icontains=search)
                    | Q(team_b__icontains=search)
                    | Q(team_c__icontains=search)
                    | Q(position__icontains=search)
                ).values_list("user_id", flat=True)
            )
            combined_ids = set(ids_from_custom) | set(ids_from_subadmin)
            qs = qs.filter(id__in=combined_ids)

        records_filtered = qs.count()
        qs = qs.order_by("name", "id")
        page_qs = qs.only("id", "name", "branch", "part")[start : start + length]

        page_ids = [u.id for u in page_qs]
        subadmin_map = {
            str(sa.user_id): {
                "position": sa.position or "-",
                "team_a": sa.team_a or "-",
                "team_b": sa.team_b or "-",
                "team_c": sa.team_c or "-",
            }
            for sa in SubAdminTemp.objects.filter(user_id__in=page_ids)
        }

        data = []
        for u in page_qs:
            sa = subadmin_map.get(str(u.id), {})
            data.append(
                {
                    "part": u.part or "-",
                    "branch": u.branch or "-",
                    "name": u.name or "-",
                    "user_id": u.id,
                    "position": sa.get("position", "-"),
                    "team_a": sa.get("team_a", "-"),
                    "team_b": sa.get("team_b", "-"),
                    "team_c": sa.get("team_c", "-"),
                }
            )

        return JsonResponse(
            {"draw": draw, "data": data, "recordsTotal": records_total, "recordsFiltered": records_filtered},
            status=200,
        )

    except Exception as e:
        traceback.print_exc()
        return JsonResponse(
            {"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0, "error": str(e)},
            status=200,
        )


@require_POST
@grade_required(["superuser", "main_admin"])
def ajax_update_level(request):
    user_id = request.POST.get("user_id")
    level = request.POST.get("level")
    try:
        sub_admin = SubAdminTemp.objects.get(user_id=user_id)
        sub_admin.level = level
        sub_admin.save(update_fields=["level"])
        return JsonResponse({"success": True})
    except SubAdminTemp.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})


# ------------------------------------------------------------
# Part/Branch utilities
# ------------------------------------------------------------
@grade_required(["superuser"])
def ajax_fetch_parts(request):
    exclude_list = ["1인GA사업부", "MA사업0부"]
    parts = (
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
        .exclude(part__in=exclude_list)
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )
    return JsonResponse({"parts": list(parts)})


@grade_required(["superuser"])
def ajax_fetch_branches(request):
    part = request.GET.get("part")
    if not part:
        return JsonResponse({"branches": []})

    branches = (
        CustomUser.objects.filter(part__iexact=part)
        .exclude(branch__isnull=True)
        .exclude(branch__exact="")
        .values_list("branch", flat=True)
        .distinct()
        .order_by("branch")
    )
    return JsonResponse({"branches": list(branches)})


# ------------------------------------------------------------
# TableSetting
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_table_fetch(request):
    branch = (request.GET.get("branch") or "").strip()
    user = request.user

    if not branch:
        return json_err("지점(branch) 정보가 없습니다.", status=400)
    if user.grade != "superuser" and branch != user.branch:
        return json_err("다른 지점 테이블에는 접근할 수 없습니다.", status=403)

    try:
        rows = (
            TableSetting.objects.filter(branch=branch)
            .order_by("order")
            .values("order", "branch", "table_name", "rate", "created_at", "updated_at")
        )
        data = [
            {
                "order": r["order"],
                "branch": r["branch"],
                "table": r["table_name"],
                "rate": r["rate"],
                "created_at": r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "-",
                "updated_at": r["updated_at"].strftime("%Y-%m-%d") if r["updated_at"] else "-",
            }
            for r in rows
        ]
        return json_ok({"rows": data})
    except Exception as e:
        traceback.print_exc()
        return json_err(f"조회 중 오류 발생: {str(e)}", status=500)


@require_POST
@grade_required(["superuser", "main_admin"])
def ajax_table_save(request):
    try:
        data = parse_json_body(request)
        branch = (data.get("branch") or "").strip()
        rows = data.get("rows", [])

        if not branch or not isinstance(rows, list):
            return json_err("요청 데이터가 잘못되었습니다.", status=400)

        with transaction.atomic():
            TableSetting.objects.filter(branch=branch).delete()

            objs = []
            for r in rows:
                order = int(r.get("order") or 0)
                table_name = (r.get("table") or "").strip()
                rate = (r.get("rate") or "").strip()
                if not table_name and not rate:
                    continue
                objs.append(TableSetting(branch=branch, table_name=table_name, rate=rate, order=order))

            TableSetting.objects.bulk_create(objs)

        return json_ok({"saved_count": len(objs)})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


# ------------------------------------------------------------
# RateTable (userlist + excel + upload + detail)
# ------------------------------------------------------------
@require_GET
def ajax_rate_userlist(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"data": []})

    users = CustomUser.objects.filter(branch=branch, is_active=True).values("id", "name", "branch").order_by("name")
    user_ids = [u["id"] for u in users]

    team_map = {
        t.user_id: {"team_a": t.team_a, "team_b": t.team_b, "team_c": t.team_c}
        for t in SubAdminTemp.objects.filter(user_id__in=user_ids)
    }
    rate_map = {
        r.user_id: {"non_life_table": r.non_life_table or "", "life_table": r.life_table or ""}
        for r in RateTable.objects.filter(user_id__in=user_ids)
    }

    data = []
    for u in users:
        team_info = team_map.get(u["id"], {})
        rate_info = rate_map.get(u["id"], {})
        data.append(
            {
                "id": u["id"],
                "name": u["name"],
                "branch": u["branch"],
                "team_a": team_info.get("team_a", ""),
                "team_b": team_info.get("team_b", ""),
                "team_c": team_info.get("team_c", ""),
                "non_life_table": rate_info.get("non_life_table", ""),
                "life_table": rate_info.get("life_table", ""),
            }
        )
    return JsonResponse({"data": data})


def ajax_rate_userlist_excel(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"error": "지점을 선택해주세요."}, status=400)

    user = request.user
    if user.grade != "superuser" and branch != user.branch:
        return JsonResponse({"error": "다른 지점 데이터에는 접근할 수 없습니다."}, status=403)

    users = list(CustomUser.objects.filter(branch=branch, is_active=True).values("id", "name", "branch").order_by("name"))
    user_ids = [u["id"] for u in users]

    team_map = {
        t.user_id: {"team_a": t.team_a, "team_b": t.team_b, "team_c": t.team_c}
        for t in SubAdminTemp.objects.filter(user_id__in=user_ids)
    }
    rate_map = {
        r.user_id: {"non_life_table": r.non_life_table or "", "life_table": r.life_table or ""}
        for r in RateTable.objects.filter(user_id__in=user_ids)
    }

    data = []
    for u in users:
        team_info = team_map.get(u["id"], {})
        rate_info = rate_map.get(u["id"], {})
        data.append(
            {
                "지점": u["branch"],
                "팀A": team_info.get("team_a", ""),
                "팀B": team_info.get("team_b", ""),
                "팀C": team_info.get("team_c", ""),
                "성명": u["name"],
                "사번": u["id"],
                "손보테이블": rate_info.get("non_life_table", ""),
                "생보테이블": rate_info.get("life_table", ""),
            }
        )

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="요율현황")

    filename = f"요율현황_{branch}_{datetime.now():%Y%m%d}.xlsx"
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_POST
@transaction.atomic
def ajax_rate_userlist_upload(request):
    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return json_err("엑셀 파일이 없습니다.", status=400)

    try:
        file_path = default_storage.save(f"tmp/{excel_file.name}", excel_file)
        file_path_full = default_storage.path(file_path)

        df = pd.read_excel(file_path_full, sheet_name="업로드").fillna("")
        required_cols = ["사번", "손보테이블", "생보테이블"]
        for col in required_cols:
            if col not in df.columns:
                default_storage.delete(file_path)
                return json_err(f"'{col}' 컬럼이 없습니다.", status=400)

        updated_count, skipped_count = 0, 0
        for _, row in df.iterrows():
            user_id = str(row["사번"]).strip()
            if not user_id:
                skipped_count += 1
                continue

            u = CustomUser.objects.filter(id=user_id).first()
            if not u:
                skipped_count += 1
                continue

            RateTable.objects.update_or_create(
                user=u,
                defaults={"non_life_table": row["손보테이블"], "life_table": row["생보테이블"]},
            )
            updated_count += 1

        default_storage.delete(file_path)
        return json_ok({"message": f"업로드 완료 ({updated_count}건 업데이트 / {skipped_count}건 스킵됨)"})
    except Exception as e:
        traceback.print_exc()
        return json_err(f"업로드 중 오류: {str(e)}", status=500)


@require_GET
def ajax_rate_user_detail(request):
    user_id = (request.GET.get("user_id") or "").strip()
    if not user_id:
        return json_err("user_id가 없습니다.", status=400)

    try:
        target = CustomUser.objects.get(id=user_id)

        rate_info = RateTable.objects.filter(user=target).first()
        non_life_table = rate_info.non_life_table if rate_info else ""
        life_table = rate_info.life_table if rate_info else ""

        non_life_rate = find_table_rate(target.branch, non_life_table)
        life_rate = find_table_rate(target.branch, life_table)

        return json_ok(
            {
                "data": {
                    "target_name": target.name,
                    "target_id": target.id,
                    "non_life_table": non_life_table,
                    "life_table": life_table,
                    "non_life_rate": non_life_rate,
                    "life_rate": life_rate,
                    "branch": target.branch or "",
                }
            }
        )
    except CustomUser.DoesNotExist:
        return json_err("대상자를 찾을 수 없습니다.", status=404)
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


@require_GET
@grade_required(["superuser", "main_admin"])
def ajax_rate_userlist_template_excel(request):
    try:
        branch = (request.GET.get("branch") or "").strip()
        df = pd.DataFrame(columns=["사번", "손보테이블", "생보테이블"])

        guide = pd.DataFrame(
            [
                ["업로드 시트명은 반드시 '업로드' 이어야 합니다.", "", ""],
                ["컬럼명은 정확히: 사번 / 손보테이블 / 생보테이블", "", ""],
                ["사번은 CustomUser.id와 매칭됩니다.", "", ""],
            ],
            columns=["안내", " ", "  "],
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="업로드")
            guide.to_excel(writer, index=False, sheet_name="안내")
            ws = writer.book["업로드"]
            ws.column_dimensions["A"].width = 14
            ws.column_dimensions["B"].width = 20
            ws.column_dimensions["C"].width = 20

        filename = f"요율현황_업로드양식_{branch+'_' if branch else ''}{datetime.now():%Y%m%d}.xlsx"
        resp = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    except Exception as e:
        traceback.print_exc()
        return json_err(f"양식 생성 오류: {str(e)}", status=500)


# ------------------------------------------------------------
# ✅ 공개 API 이름(신규 네이밍) + Legacy alias 연결
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def structure_fetch(request):
    return ajax_fetch(request)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def structure_save(request):
    return ajax_save(request)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def structure_delete(request):
    return ajax_delete(request)


def join_form(request): return render(request, "partner/join_form.html")