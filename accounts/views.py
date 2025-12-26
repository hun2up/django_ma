# django_ma/accounts/views.py

from django.shortcuts import render
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth.views import LoginView
from django.urls import reverse

# Create your views here.
def upload_progress_view(request):
    task_id = request.GET.get("task_id", "").strip()
    if not task_id:
        return JsonResponse({"percent": 0, "status": "PENDING"})

    percent = cache.get(f"upload_progress:{task_id}", 0)
    status = cache.get(f"upload_status:{task_id}", "PENDING")
    error = cache.get(f"upload_error:{task_id}", "")

    download_url = ""
    if status == "SUCCESS":
        download_url = reverse("admin:upload_users_result", args=[task_id])

    return JsonResponse({
        "percent": percent,
        "status": status,
        "error": error,
        "download_url": download_url,
    })

class SessionCloseLoginView(LoginView):
    """로그인 시 세션을 브라우저 종료 시 만료로 강제"""
    def form_valid(self, form):
        response = super().form_valid(form)
        # 0 → 브라우저 닫으면 즉시 세션 만료
        self.request.session.set_expiry(0)
        return response