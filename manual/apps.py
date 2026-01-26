# django_ma/manual/apps.py

from django.apps import AppConfig


class ManualConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "manual"
    verbose_name = "업무 매뉴얼"

    # signals를 쓸 예정이면 아래 주석 해제
    # def ready(self):
    #     import manual.signals  # noqa
