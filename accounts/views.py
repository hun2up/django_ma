# django_ma/accounts/views.py
from __future__ import annotations

from django.core.cache import cache
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib.auth.views import LoginView
from django.urls import reverse


def upload_progress_view(request: HttpRequest) -> JsonResponse:
    """
    업로드/처리 진행률 조회 API
    - cache key:
        upload_progress:{task_id} -> int(0~100)
        upload_status:{task_id}   -> str(PENDING|STARTED|SUCCESS|FAILURE...)
        upload_error:{task_id}    -> str
    """
    task_id = (request.GET.get("task_id") or "").strip()
    if not task_id:
        return JsonResponse({"percent": 0, "status": "PENDING", "error": "", "download_url": ""})

    percent = cache.get(f"upload_progress:{task_id}", 0)
    status = cache.get(f"upload_status:{task_id}", "PENDING")
    error = cache.get(f"upload_error:{task_id}", "")

    download_url = ""
    # ✅ admin 쪽에 결과 페이지가 있는 경우만 URL 생성
    if status == "SUCCESS":
        try:
            download_url = reverse("admin:upload_users_result", args=[task_id])
        except Exception:
            download_url = ""

    return JsonResponse(
        {
            "percent": int(percent or 0),
            "status": status or "PENDING",
            "error": error or "",
            "download_url": download_url,
        }
    )


class SessionCloseLoginView(LoginView):
    """
    로그인 성공 시 세션을 브라우저 종료 시 만료되도록 강제(set_expiry=0).
    """
    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        self.request.session.set_expiry(0)
        return response
