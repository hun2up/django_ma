# django_ma/manual/views/block.py

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..models import ManualBlock, ManualSection
from ..utils import block_to_dict, fail, is_digits, json_body, ok, ensure_superuser_or_403


@require_POST
@login_required
def manual_block_add_ajax(request):
    """superuser 전용: 블록 추가 (multipart)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    manual_id = request.POST.get("manual_id")
    section_id = request.POST.get("section_id")
    content = request.POST.get("content", "")
    image = request.FILES.get("image")

    if not (is_digits(manual_id) and is_digits(section_id)):
        return fail("요청값이 올바르지 않습니다.", 400)

    try:
        sec = ManualSection.objects.get(id=int(section_id), manual_id=int(manual_id))
    except ManualSection.DoesNotExist:
        return fail("섹션을 찾을 수 없습니다.", 404)

    last_order = ManualBlock.objects.filter(section=sec).count()

    b = ManualBlock.objects.create(
        manual=sec.manual,  # 기존 호환 유지
        section=sec,
        content=content,
        image=image if image else None,
        sort_order=last_order + 1,
    )

    return ok({"block": block_to_dict(b)})


@require_POST
@login_required
def manual_block_update_ajax(request):
    """superuser 전용: 블록 수정 (multipart)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    block_id = request.POST.get("block_id")
    content = request.POST.get("content", "")
    remove_image = request.POST.get("remove_image", "0")
    image = request.FILES.get("image")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(
        ManualBlock.objects.select_related("section__manual").prefetch_related("attachments"),
        id=int(block_id),
    )

    with transaction.atomic():
        b.content = content

        if remove_image == "1":
            if b.image:
                b.image.delete(save=False)
            b.image = None

        if image:
            if b.image:
                b.image.delete(save=False)
            b.image = image

        b.save()

    return ok({"block": block_to_dict(b)})


@require_POST
@login_required
def manual_block_delete_ajax(request):
    """superuser 전용: 블록 삭제 (JSON)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    block_id = payload.get("block_id")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(ManualBlock.objects.prefetch_related("attachments"), pk=int(block_id))
    b.delete()  # 이미지/첨부 파일은 모델 delete에서 처리(기존 전제 유지)

    return ok()


@require_POST
@login_required
def manual_block_reorder_ajax(request):
    """superuser 전용: 블록 순서 저장(섹션 단위)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")
    block_ids = payload.get("block_ids") or []

    if not is_digits(section_id) or not isinstance(block_ids, list):
        return fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualBlock.objects.filter(section_id=int(section_id))
    existing = set(qs.values_list("id", flat=True))
    cleaned = [int(bid) for bid in block_ids if is_digits(bid) and int(bid) in existing]

    with transaction.atomic():
        for idx, bid in enumerate(cleaned, start=1):
            ManualBlock.objects.filter(id=bid).update(sort_order=idx)

    return ok()


@require_POST
@login_required
def manual_block_move_ajax(request):
    """superuser 전용: 블록을 다른 섹션으로 이동 + 양쪽 정렬 저장"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    from_section_id = payload.get("from_section_id")
    to_section_id = payload.get("to_section_id")
    from_block_ids = payload.get("from_block_ids") or []
    to_block_ids = payload.get("to_block_ids") or []

    if (not is_digits(from_section_id)) or (not is_digits(to_section_id)):
        return fail("section_id 값이 올바르지 않습니다.", 400)
    if (not isinstance(from_block_ids, list)) or (not isinstance(to_block_ids, list)):
        return fail("block_ids 형식이 올바르지 않습니다.", 400)

    from_sid = int(from_section_id)
    to_sid = int(to_section_id)

    from_sec = get_object_or_404(ManualSection, pk=from_sid)
    to_sec = get_object_or_404(ManualSection, pk=to_sid)

    if from_sec.manual_id != to_sec.manual_id:
        return fail("서로 다른 매뉴얼 간 이동은 허용되지 않습니다.", 400)

    union_ids = set(
        ManualBlock.objects.filter(section_id__in=[from_sid, to_sid]).values_list("id", flat=True)
    )

    cleaned_from = [int(x) for x in from_block_ids if is_digits(x) and int(x) in union_ids]
    cleaned_to = [int(x) for x in to_block_ids if is_digits(x) and int(x) in union_ids]

    if not cleaned_to:
        return fail("이동 대상 블록 목록이 비어있습니다.", 400)

    with transaction.atomic():
        ManualBlock.objects.filter(id__in=cleaned_to).update(section_id=to_sid)

        for idx, bid in enumerate(cleaned_from, start=1):
            ManualBlock.objects.filter(id=bid, section_id=from_sid).update(sort_order=idx)

        for idx, bid in enumerate(cleaned_to, start=1):
            ManualBlock.objects.filter(id=bid, section_id=to_sid).update(sort_order=idx)

    return ok()
