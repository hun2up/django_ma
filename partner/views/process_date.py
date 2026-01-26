# partner/views/process_date.py
# ------------------------------------------------------------
# ✅ 처리일자(process_date) 업데이트 공용 로직
# - record 먼저 로드 후 branch 검사(기존 주석 유지)
# - head는 자기 지점만 수정 가능
# ------------------------------------------------------------

from typing import Optional, Type

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required

from partner.models import EfficiencyChange, PartnerChangeLog, RateChange, StructureChange

from .responses import json_err, json_ok, parse_json_body
from .utils import parse_yyyy_mm_dd_or_none


def _resolve_process_model(kind: str) -> Optional[Type]:
    k = (kind or "").strip().lower()
    if k == "structure":
        return StructureChange
    if k == "rate":
        return RateChange
    if k == "efficiency":
        return EfficiencyChange
    return None


def _update_process_date_common(*, request, kind: str, record_id, new_date: str):
    if not record_id:
        return json_err("id 누락", status=400)

    model = _resolve_process_model(kind)
    if model is None:
        return json_err(f"지원하지 않는 kind: {kind}", status=400)

    record = get_object_or_404(model, id=record_id)

    # ✅ head 지점 제한
    if request.user.grade == "head":
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
@login_required
@grade_required("superuser", "head")
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
@login_required
@grade_required("superuser", "head")
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
@login_required
@grade_required("superuser", "head")
@transaction.atomic
def efficiency_update_process_date(request):
    payload = parse_json_body(request)
    return _update_process_date_common(
        request=request,
        kind="efficiency",
        record_id=payload.get("id"),
        new_date=(payload.get("process_date") or "").strip(),
    )
