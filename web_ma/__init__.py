"""
Celery app을 Django 시작 시 자동 로드되도록 export합니다.
"""

# django_ma/web_ma/__init__.py

from .celery import app as celery_app

__all__ = ("celery_app",)
