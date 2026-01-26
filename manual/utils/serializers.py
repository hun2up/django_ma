# django_ma/manual/utils/serializers.py

from __future__ import annotations

import os

from manual.models import ManualBlock, ManualBlockAttachment


def attachment_to_dict(a: ManualBlockAttachment) -> dict:
    return {
        "id": a.id,
        "name": a.original_name or os.path.basename(a.file.name) if a.file else "",
        "url": a.file.url if a.file else "",
        "size": a.size or 0,
    }


def block_to_dict(b: ManualBlock) -> dict:
    """
    ✅ 블록을 프런트가 즉시 DOM 업데이트 가능한 dict로 변환
    - 이미지 + 첨부파일 포함
    """
    return {
        "id": b.id,
        "section_id": b.section_id,
        "title": b.title,
        "content": b.content,
        "image_url": b.image.url if b.image else "",
        "attachments": [
            attachment_to_dict(a)
            for a in b.attachments.all().order_by("created_at", "id")
        ],
    }
