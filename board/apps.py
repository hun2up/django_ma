# django_ma/board/apps.py

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class BoardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "board"

    def ready(self):
        """
        signals 로딩 실패 시에도 앱 구동은 유지(로그만 남김)
        """
        try:
            import board.signals  # noqa
        except Exception as e:
            logger.exception("board.signals import failed: %s", e)
