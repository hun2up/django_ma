# partner/views/rate.py
# ------------------------------------------------------------
# ✅ RateChange(요율변경 요청) API
# ------------------------------------------------------------

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from partner.models import RateChange, RateTable

from .responses import json_err, json_ok, parse_json_body
from .utils import (
    find_table_rate,
    get_level_team_filter_user_ids,
    normalize_month,
    resolve_branch_for_query,
    resolve_branch_for_write,
    resolve_part_for_write,
)


@require_GET
@login_required
@grade_required("superuser", "head", "leader")
def rate_fetch(request):
    """✅ RateChange 조회"""
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

    if user.grade == "leader":
        allowed_ids = get_level_team_filter_user_ids(user)
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
@login_required
@grade_required("superuser", "head", "leader")
@transaction.atomic
def rate_save(request):
    """✅ RateChange 저장"""
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
@login_required
@grade_required("superuser", "head")
@transaction.atomic
def rate_delete(request):
    """✅ RateChange 삭제"""
    data = parse_json_body(request)
    record_id = data.get("id")
    if not record_id:
        return json_err("id 누락", status=400)

    rc = get_object_or_404(RateChange, id=record_id)
    user = request.user

    if not (user.grade in ["superuser", "head"] or rc.requester_id == user.id):
        return json_err("삭제 권한이 없습니다.", status=403)

    rc.delete()
    return json_ok({})
