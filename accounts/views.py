from django.shortcuts import render
from django.core.cache import cache
from django.http import JsonResponse

# Create your views here.
def upload_progress_view(request):
    """업로드 진행률을 반환하는 API"""
    percent = cache.get("upload_progress", 0)
    return JsonResponse({"percent": percent})