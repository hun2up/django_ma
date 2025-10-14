# join/tasks.py
from celery import shared_task
from .pdf_utils import fill_pdf

@shared_task
def generate_pdf_task(template_path, data):
    return fill_pdf(template_path, data)
