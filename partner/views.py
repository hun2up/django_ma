# django_ma/partner/views.py
# ------------------------------------------------------------
# ✅ Final Refactor (2025-12-30)
# - manage_* Boot/context 주입 통일(build_manage_context)
# - process_date 공용 업데이트: kind -> 모델 매핑 통일
# - 구조/요율/효율 CRUD 패턴 공통화 + 프론트(fetch.js) 기대키 유지
# - ✅ 권한관리(superuser): 부서 + 지점 선택 필터 반영 (manage_grades + ajax_users_data)
# - ✅ DataTables serverSide 표준(draw 포함) 응답
# - 불필요 import 정리, 예외/응답 형식 통일
# ------------------------------------------------------------

import io
import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Type

import pandas as pd
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import (
    EfficiencyChange,
    PartnerChangeLog,
    RateChange,
    RateTable,
    StructureChange,
    SubAdminTemp,
    TableSetting,
)

# ------------------------------------------------------------
# ✅ 공용 상수
# - superuser 권한관리: part -> branches 구조가 필요
# - main_admin에서 "branch -> part 역추적"도 필요
# ------------------------------------------------------------
BRANCH_PARTS: Dict[str, list] = {
    "MA사업1부": [],
    "MA사업2부": [],
    "MA사업3부": [],
    "MA사업4부": [],
    "MA사업5부": [],
}

# ------------------------------------------------------------
# 공용 응답/파서
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
# 공용 유틸
# ------------------------------------------------------------
def get_now_ym() -> Tuple[int, int]:
    now = datetime.now()
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
    """
    조회(branch 필터) 규칙:
    - superuser: branch_param 허용
    - main/sub: 무조건 user.branch
    """
    branch_param = (branch_param or "").strip()
    if getattr(user, "grade", "") == "superuser":
        return branch_param
    return (getattr(user, "branch", "") or "").strip()


def resolve_branch_for_write(user: CustomUser, branch_payload: str) -> str:
    """
    저장 규칙:
    - superuser: payload branch 사용
    - main/sub: 무조건 user.branch
    """
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
    표기 규칙:
    - team_a가 없거나 '-'면: user.branch
    - team_a가 있으면: 'team_a team_b team_c' (단, team_b/team_c가 '-'면 제외)
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


def find_table_rate(branch: str, table_name: str) -> str:
    table_name = (table_name or "").strip()
    if not table_name:
        return ""
    ts = TableSetting.objects.filter(branch=branch, table_name=table_name).order_by("order").first()
    return (ts.rate or "") if ts else ""


def _find_part_by_branch(branch: str) -> str:
    """
    ✅ main_admin: 템플릿/JS에서 selected_part가 비어 있으면
    DataTables 초기화 자체가 생략되므로,
    branch -> part 역추적으로 selected_part를 반드시 만들어준다.
    """
    b = (branch or "").strip()
    if not b:
        return ""
    # 1) DB 기반 역추적 (가장 정확)
    p = (
        CustomUser.objects.filter(branch__iexact=b)
        .exclude(part__isnull=True)
        .exclude(part__exact="")
        .values_list("part", flat=True)
        .first()
    )
    if p:
        return str(p).strip()

    # 2) 상수 기반(혹시 상수에 실제 지점 목록을 채우는 형태라면 사용)
    for part, branches in BRANCH_PARTS.items():
        if b in (branches or []):
            return part
    return ""


def build_manage_context(
    *,
    request,
    page_kind: str,  # "structure" | "rate" | "efficiency"
    template_name: str,
    fetch_name: str,
    save_name: str,
    delete_name: str,
    update_process_name: str,
    boot_key: str,
    extra_context: Optional[Dict[str, Any]] = None,
):
    """
    ✅ 세 페이지(편제/요율/효율) 공통 컨텍스트 주입 통일
    """
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
        delete_name="partner:efficiency_delete",
        update_process_name="partner:efficiency_update_process_date",
        boot_key="ManageefficiencyBoot",
        extra_context={"search_user_url": "/api/accounts/search-user/"},
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
            # 기존 템플릿에서 branches를 "부서 목록"처럼 쓰는 경우가 있어 안전하게 내려줌
            "branches": sorted(list(BRANCH_PARTS.keys())),
            "selected_branch": selected_branch,
            "subadmin_info": subadmin_info,
        },
    )


# ------------------------------------------------------------
# Structure (편제) - legacy core (ajax_*)
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

        rows = []
        for sc in qs:
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
# ✅ 처리일자 수정 (편제/요율/효율 공용)
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


@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def ajax_update_process_date(request):
    try:
        payload = parse_json_body(request)
        record_id = payload.get("id")
        new_date = (payload.get("process_date") or "").strip()
        kind = (payload.get("kind") or payload.get("type") or "structure").strip().lower()

        if not record_id:
            return json_err("id 누락", status=400)

        if new_date == "":
            parsed_date = None
        else:
            try:
                parsed_date = parse_yyyy_mm_dd_or_none(new_date)
            except ValueError:
                return json_err("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)", status=400)

        model = _resolve_process_model(kind)
        if model is None:
            return json_err(f"지원하지 않는 kind: {kind}", status=400)

        record = get_object_or_404(model, id=record_id)
        record.process_date = parsed_date
        record.save(update_fields=["process_date"])

        PartnerChangeLog.objects.create(
            user=request.user,
            action="update_process_date",
            detail=f"[{kind}] ID {record_id} 처리일자 수정 → {new_date or 'NULL'}",
        )

        return json_ok({"message": "처리일자 변경 완료", "process_date": new_date})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=400)


# ------------------------------------------------------------
# Efficiency (지점효율) - 전용 API
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def efficiency_fetch(request):
    try:
        user = request.user
        month = normalize_month(request.GET.get("month") or "")
        branch_param = (request.GET.get("branch") or "").strip()
        branch = resolve_branch_for_query(user, branch_param)

        qs = EfficiencyChange.objects.filter(month=month).select_related("requester", "target")
        if user.grade == "superuser":
            if branch:
                qs = qs.filter(branch__iexact=branch)
        else:
            qs = qs.filter(branch__iexact=branch)

        rows = []
        for ec in qs:
            rows.append(
                {
                    "id": ec.id,
                    "requester_id": getattr(ec.requester, "id", "") if ec.requester else "",
                    "requester_name": getattr(ec.requester, "name", "") if ec.requester else "",
                    "requester_branch": build_affiliation_display(ec.requester) if ec.requester else "",
                    "target_id": getattr(ec.target, "id", "") if ec.target else "",
                    "target_name": getattr(ec.target, "name", "") if ec.target else "",
                    "target_branch": ec.target_branch or "",
                    "chg_branch": ec.chg_branch or "",
                    "rank": ec.rank or "",
                    "chg_rank": ec.chg_rank or "",
                    "or_flag": bool(ec.or_flag),
                    "memo": ec.memo or "",
                    "request_date": ec.created_at.strftime("%Y-%m-%d") if ec.created_at else "",
                    "process_date": ec.process_date.strftime("%Y-%m-%d") if ec.process_date else "",
                }
            )

        return json_ok({"kind": "efficiency", "rows": rows})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500, extra={"rows": []})


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def efficiency_save(request):
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

            EfficiencyChange.objects.create(
                requester=user,
                target=target,
                part=part,
                branch=branch,
                month=month,
                target_branch=build_affiliation_display(target),
                chg_branch=(row.get("chg_branch") or row.get("after_branch") or "").strip(),
                rank=(row.get("tg_rank") or row.get("rank") or "").strip(),
                chg_rank=(row.get("chg_rank") or row.get("after_rank") or "").strip(),
                or_flag=bool(row.get("or_flag", False)),
                memo=(row.get("memo") or "").strip(),
            )
            created_count += 1

        PartnerChangeLog.objects.create(
            user=user,
            action="save",
            detail=f"{created_count}건 저장 (efficiency / 월:{month} / 부서:{part} / 지점:{branch})",
        )

        return json_ok({"saved_count": created_count})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=400)


@require_POST
@grade_required(["superuser", "main_admin"])  # 정책: sub_admin 삭제 불가
@transaction.atomic
def efficiency_delete(request):
    try:
        data = parse_json_body(request)
        record_id = data.get("id")
        if not record_id:
            return json_err("id 누락", status=400)

        record = get_object_or_404(EfficiencyChange, id=record_id)
        record.delete()
        return json_ok({})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


# ------------------------------------------------------------
# ✅ 권한관리 (superuser: 부서 + 지점 선택)
# ------------------------------------------------------------
@grade_required(["superuser", "main_admin"])
def manage_grades(request):
    user = request.user

    LEVELS = ["-", "A레벨", "B레벨", "C레벨"]
    parts = sorted(list(BRANCH_PARTS.keys()))

    # ✅ 기본값
    selected_part = (request.GET.get("part") or "").strip()
    selected_branch = (request.GET.get("branch") or "").strip()

    base_sub_admin_users = CustomUser.objects.filter(grade="sub_admin")

    if user.grade == "superuser":
        # superuser는 part+branch 둘 다 있어야만 조회
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
        # ✅ main_admin은 지점 고정 + part는 역추적으로 반드시 채움
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
    """
    ✅ 업로드 후에도 superuser의 part/branch 필터 상태 유지하도록 redirect 개선
    """
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

            # 필요없으면 제거
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
    """
    ✅ DataTables serverSide (표준 응답)
    - superuser: part + branch 필터 지원
    - main_admin: branch 고정 (+ part 미전달 시 branch로 역추적)
    """
    user = request.user

    # DataTables 필수: draw
    try:
        draw = int(request.GET.get("draw", "1") or "1")
    except ValueError:
        draw = 1

    # paging
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
        # ✅ base_qs 결정
        if user.grade == "superuser":
            # superuser는 part/branch 둘 중 하나라도 없으면 "빈 결과"로 반환(테이블 멈춤 방지)
            if not selected_part or not selected_branch:
                return JsonResponse(
                    {"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0},
                    status=200,
                )

            base_qs = CustomUser.objects.filter(part=selected_part, branch=selected_branch)

        else:
            # main_admin: 지점 고정
            fixed_branch = (user.branch or "").strip()
            if not fixed_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)

            base_qs = CustomUser.objects.filter(branch=fixed_branch)

            # selected_part가 비어도 괜찮지만, 엑셀다운로드(fetch length=999999) 같은 호출에서
            # part가 필요해지는 경우를 대비해 역추적(옵션)
            if not selected_part:
                selected_part = _find_part_by_branch(fixed_branch) or (user.part or "").strip()

        records_total = base_qs.count()
        qs = base_qs

        # ✅ search: CustomUser 필드 + SubAdminTemp(team/position) 포함 검색
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
            {
                "draw": draw,
                "data": data,
                "recordsTotal": records_total,
                "recordsFiltered": records_filtered,
            },
            status=200,
        )

    except Exception as e:
        traceback.print_exc()
        # DataTables는 에러에도 draw가 있으면 화면이 덜 깨짐
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
# RateTable(요율현황)
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

    users = list(
        CustomUser.objects.filter(branch=branch, is_active=True).values("id", "name", "branch").order_by("name")
    )
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
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_POST
@transaction.atomic
def ajax_rate_userlist_upload(request):
    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return json_err("엑셀 파일이 없습니다.", status=400)

    try:
        from django.core.files.storage import default_storage

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


# ------------------------------------------------------------
# RateChange (요율변경) - 전용 API
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


@require_GET
@grade_required(["superuser", "main_admin"])
def ajax_rate_userlist_template_excel(request):
    """
    ✅ 업로드 최적화 빈 양식 다운로드
    - sheet_name = "업로드"
    - columns = ["사번", "손보테이블", "생보테이블"]
    """
    try:
        # (선택) branch를 파일명에만 반영
        branch = (request.GET.get("branch") or "").strip()

        # 빈 템플릿 + 안내용 예시 1줄(원하면 제거 가능)
        df = pd.DataFrame(columns=["사번", "손보테이블", "생보테이블"])

        # 안내 시트(선택): 사용자가 실수 줄이게 도움
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

            # 보기 좋게 열 너비(선택)
            ws = writer.book["업로드"]
            ws.column_dimensions["A"].width = 14
            ws.column_dimensions["B"].width = 20
            ws.column_dimensions["C"].width = 20

        filename = f"요율현황_업로드양식_{branch+'_' if branch else ''}{datetime.now():%Y%m%d}.xlsx"
        resp = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    except Exception as e:
        traceback.print_exc()
        return json_err(f"양식 생성 오류: {str(e)}", status=500)


# ------------------------------------------------------------
# Structure endpoints (전용 alias)
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
