from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_ma.settings')

app = Celery('web_ma', broker='redis://localhost:6379/0')
app.conf.worker_pool = 'solo'
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')