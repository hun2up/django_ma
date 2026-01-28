# django_ma/board/signals.py

import os
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Attachment, TaskAttachment


def _safe_delete_file(file_field):
    """
    FileField 실제 파일 삭제 공용 유틸
    """
    if not file_field:
        return
    file_path = getattr(file_field, "path", None)
    if not file_path:
        return
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception:
            # signals에서는 조용히 실패(운영 환경에서 파일락/권한 이슈 가능)
            pass


@receiver(post_delete, sender=Attachment)
def delete_post_attachment_file(sender, instance, **kwargs):
    """
    Post Attachment 삭제 시 실제 파일도 삭제
    """
    _safe_delete_file(getattr(instance, "file", None))


@receiver(post_delete, sender=TaskAttachment)
def delete_task_attachment_file(sender, instance, **kwargs):
    """
    Task Attachment 삭제 시 실제 파일도 삭제
    """
    _safe_delete_file(getattr(instance, "file", None))
