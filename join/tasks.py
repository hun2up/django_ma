# manual/tasks.py
from celery import shared_task
from .pdf_utils import fill_pdf
import time
import os  # ⬅️ 누락되었음. 파일 삭제에 필요

@shared_task
def generate_pdf_task(template_path, data):
    return fill_pdf(template_path, data)

@shared_task
def delete_file_task(file_path, delay=10):
    time.sleep(delay)
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"[삭제 실패] {e}")
