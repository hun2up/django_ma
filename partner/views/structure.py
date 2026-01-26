# partner/views/structure.py
# ------------------------------------------------------------
# ✅ Structure(편제변경) API
# - core: ajax_save/ajax_delete/ajax_fetch
# - 신규 네이밍: structure_save/structure_delete/structure_fetch (legacy alias 유지)
# ------------------------------------------------------------

import traceback

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from partner.models import PartnerChangeLog, StructureChange

from .responses import json_err, json_ok, parse_json_body
from .utils import (
    build_affiliation_display,
    get_level_team_filter_user_ids,
    normalize_month,
    resolve_branch_for_query,
    resolve_branch_for_write,
    resolve_part_for_write,
)


@require_POST
@login_required
@grade_required("superuser", "head", "leader")
@transaction.atomic
def ajax_save(request):
    """✅ Structure 저장"""
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
@login_required
@grade_required("superuser", "head", "leader")
@transaction.atomic
def ajax_delete(request):
    """✅ Structure 단건 삭제"""
    try:
        data = parse_json_body(request)
        record_id = data.get("id")
        if not record_id:
            return json_err("id 누락", status=400)

        record = get_object_or_404(StructureChange, id=record_id)
        user = request.user

        if not (user.grade in ["superuser", "head"] or record.requester_id == user.id):
            return json_err("삭제 권한이 없습니다.", status=403)

        deleted_id = record.id
        record.delete()

        PartnerChangeLog.objects.create(user=user, action="delete", detail=f"StructureChange #{deleted_id} 삭제")
        return json_ok({"message": f"#{deleted_id} 삭제 완료"})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


@require_GET
@login_required
@grade_required("superuser", "head", "leader")
def ajax_fetch(request):
    """✅ Structure 조회 (권한 스코프 동일 유지)"""
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

        if user.grade == "leader":
            allowed_ids = get_level_team_filter_user_ids(user)
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
# ✅ 신규 API 이름 + Legacy alias
# ------------------------------------------------------------
@require_GET
@login_required
@grade_required("superuser", "head", "leader")
def structure_fetch(request):
    return ajax_fetch(request)


@require_POST
@login_required
@grade_required("superuser", "head", "leader")
@transaction.atomic
def structure_save(request):
    return ajax_save(request)


@require_POST
@login_required
@grade_required("superuser", "head", "leader")
@transaction.atomic
def structure_delete(request):
    return ajax_delete(request)
