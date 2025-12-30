# django_ma/board/apps.py

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class BoardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "board"

    def ready(self):
        try:
            import board.signals  # noqa
        except Exception as e:
            logger.exception("board.signals import failed: %s", e)
