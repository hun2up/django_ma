# ===========================================
# 📂 board/signals.py — 첨부파일 삭제 시 실제 파일도 삭제
# ===========================================

import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Attachment


@receiver(post_delete, sender=Attachment)
def delete_attachment_file(sender, instance, **kwargs):
    """
    Attachment 객체 삭제 시 실제 파일도 함께 삭제
    (DB 삭제 → 파일 삭제 동기화)
    """
    file_path = instance.file.path
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            print(f"🗑️ 첨부파일 삭제 완료: {file_path}")
        except Exception as e:
            print(f"⚠️ 첨부파일 삭제 실패: {file_path} ({e})")
