import os
from celery import Celery

# Django 프로젝트의 settings 모듈 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_ma.settings")

# Celery 앱 생성
app = Celery("web_ma")

# Django 설정에서 CELERY로 시작하는 설정 불러오기
app.config_from_object("django.conf:settings", namespace="CELERY")

# 모든 Django 앱의 tasks.py 모듈 자동 탐색
app.autodiscover_tasks()
