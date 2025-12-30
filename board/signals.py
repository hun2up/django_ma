# django_ma/board/signals.py
# ===========================================
# 📂 board/signals.py — 첨부파일 삭제 시 실제 파일도 삭제
# ===========================================

import os
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender="board.Attachment")
def delete_attachment_file(sender, instance, **kwargs):
    """
    Attachment 객체 삭제 시 실제 파일도 함께 삭제
    (DB 삭제 → 파일 삭제 동기화)
    """
    # FileField가 비어있을 수도 있으니 안전 처리
    f = getattr(instance, "file", None)
    if not f:
        return

    file_path = getattr(f, "path", None)
    if not file_path:
        return

    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ 첨부파일 삭제 완료: {file_path}")
        except Exception as e:
            print(f"⚠️ 첨부파일 삭제 실패: {file_path} ({e})")
