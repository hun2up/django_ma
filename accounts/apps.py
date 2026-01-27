# django_ma/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        # ✅ signals 등록 (앱 로드 시 1회)
        from . import signals  # noqa