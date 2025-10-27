# django_ma/partner/apps.py
from django.apps import AppConfig


class PartnerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "partner"

    def ready(self):
        """
        ✅ 앱 로드 시 signals 등록
        """
        import partner.signals
