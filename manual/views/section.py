# django_ma/manual/views/section.py

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..constants import SECTION_TITLE_MAX_LEN
from ..models import Manual, ManualSection
from ..utils import ensure_default_section, fail, is_digits, json_body, ok, to_str, ensure_superuser_or_403


@require_POST
@login_required
def manual_section_add_ajax(request):
    """superuser 전용: 섹션(카드) 추가"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    manual_id = payload.get("manual_id")

    if not is_digits(manual_id):
        return fail("manual_id가 올바르지 않습니다.", 400)

    m = get_object_or_404(Manual, pk=int(manual_id))
    last = m.sections.order_by("-sort_order", "-id").first()
    next_order = (last.sort_order if last else 0) + 1

    sec = ManualSection.objects.create(manual=m, sort_order=next_order, title="")

    return ok(
        {"section": {"id": sec.id, "sort_order": sec.sort_order, "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M")}}
    )


@require_POST
@login_required
def manual_section_title_update_ajax(request):
    """superuser 전용: 섹션 소제목(title) 수정"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")
    title = to_str(payload.get("title"))

    if not is_digits(section_id):
        return fail("section_id가 올바르지 않습니다.", 400)
    if len(title) > SECTION_TITLE_MAX_LEN:
        return fail(f"소제목은 최대 {SECTION_TITLE_MAX_LEN}자까지 가능합니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    sec.title = title
    sec.save(update_fields=["title", "updated_at"])

    return ok({"section": {"id": sec.id, "title": sec.title, "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M")}})


@require_POST
@login_required
def manual_section_delete_ajax(request):
    """superuser 전용: 섹션 삭제 (0개가 되면 기본 섹션 자동 생성)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")

    if not is_digits(section_id):
        return fail("section_id가 올바르지 않습니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    manual = sec.manual
    sec.delete()

    new_section = None
    if manual.sections.count() == 0:
        created = ensure_default_section(manual)
        new_section = {"id": created.id, "title": created.title or ""}

    return ok({"new_section": new_section})


@require_POST
@login_required
def manual_section_reorder_ajax(request):
    """superuser 전용: 섹션(카드) 순서 저장"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    manual_id = payload.get("manual_id")
    section_ids = payload.get("section_ids") or []

    if not is_digits(manual_id) or not isinstance(section_ids, list):
        return fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualSection.objects.filter(manual_id=int(manual_id))
    existing = set(qs.values_list("id", flat=True))

    cleaned = [int(sid) for sid in section_ids if is_digits(sid) and int(sid) in existing]

    with transaction.atomic():
        for idx, sid in enumerate(cleaned, start=1):
            ManualSection.objects.filter(id=sid).update(sort_order=idx)

    return ok()
