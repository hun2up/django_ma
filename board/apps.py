# board/apps.py

from django.apps import AppConfig

class BoardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "board"

    def ready(self):
        # ✅ signals.py 자동 로드
        import board.signals
