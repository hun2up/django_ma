# django_ma/manual/views/attachment.py

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..constants import MAX_ATTACHMENT_SIZE
from ..models import ManualBlock, ManualBlockAttachment
from ..utils import fail, is_digits, json_body, ok, to_str, ensure_superuser_or_403, attachment_to_dict


@require_POST
@login_required
def manual_block_attachment_upload_ajax(request):
    """superuser 전용: 블록 첨부 업로드 (multipart)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    block_id = request.POST.get("block_id")
    upfile = request.FILES.get("file")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)
    if not upfile:
        return fail("업로드할 파일이 없습니다.", 400)

    if upfile.size and upfile.size > MAX_ATTACHMENT_SIZE:
        mb = int(MAX_ATTACHMENT_SIZE / (1024 * 1024))
        return fail(f"파일 용량은 최대 {mb}MB까지 가능합니다.", 400)

    b = get_object_or_404(ManualBlock, pk=int(block_id))

    a = ManualBlockAttachment.objects.create(
        block=b,
        file=upfile,
        original_name=to_str(getattr(upfile, "name", "")),
        size=int(getattr(upfile, "size", 0) or 0),
    )

    # 기존 직렬화 형태 유지
    return ok({"attachment": attachment_to_dict(a)})


@require_POST
@login_required
def manual_block_attachment_delete_ajax(request):
    """superuser 전용: 첨부 삭제 (JSON)"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    attachment_id = payload.get("attachment_id")

    if not is_digits(attachment_id):
        return fail("attachment_id가 올바르지 않습니다.", 400)

    a = get_object_or_404(ManualBlockAttachment, pk=int(attachment_id))
    a.delete()
    return ok()
