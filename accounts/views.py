# django_ma/accounts/views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse

from .constants import (
    CACHE_ERROR_PREFIX,
    CACHE_PROGRESS_PREFIX,
    CACHE_RESULT_PATH_PREFIX,
    CACHE_STATUS_PREFIX,
    cache_key,
)
from .forms import ActiveOnlyAuthenticationForm
from .search_api import search_users_for_api


# =============================================================================
# Upload Progress (Excel 업로드 진행률 / 상태 조회)
# =============================================================================

@login_required
def upload_progress_view(request: HttpRequest) -> JsonResponse:
    task_id = (request.GET.get("task_id") or "").strip()
    if not task_id:
        return JsonResponse({"percent": 0, "status": "PENDING", "error": "", "download_url": ""})

    percent = cache.get(cache_key(CACHE_PROGRESS_PREFIX, task_id), 0) or 0
    status = cache.get(cache_key(CACHE_STATUS_PREFIX, task_id), "PENDING") or "PENDING"
    error = cache.get(cache_key(CACHE_ERROR_PREFIX, task_id), "") or ""

    download_url = ""
    if status == "SUCCESS":
        try:
            download_url = reverse("admin:upload_users_result", args=[task_id])
        except Exception:
            download_url = ""

    return JsonResponse(
        {
            "percent": int(percent),
            "status": str(status),
            "error": str(error),
            "download_url": download_url,
        }
    )


# =============================================================================
# Auth (로그인 후 브라우저 종료 시 세션 만료)
# =============================================================================

class SessionCloseLoginView(LoginView):
    authentication_form = ActiveOnlyAuthenticationForm

    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        self.request.session.set_expiry(0)
        return response


# =============================================================================
# User Search API (SSOT 호출 wrapper)
# =============================================================================

@login_required
def api_search_user(request: HttpRequest) -> JsonResponse:
    """
    ✅ 정식 검색 구현(search_api.search_users_for_api)을 호출하는 thin wrapper
    """
    return JsonResponse(search_users_for_api(request))


# ✅ 레거시 alias (기존 /search-user/ 유지)
@login_required
def search_user(request: HttpRequest) -> JsonResponse:
    return api_search_user(request)
