# web_ma/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_ma.settings")

app = Celery("web_ma")
app.config_from_object("django.conf:settings", namespace="CELERY")

# ✅ 모든 INSTALLED_APPS에서 tasks.py 자동 탐색
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
