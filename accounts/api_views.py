# django_ma/accounts/api_views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse

from .search_api import search_users_for_api


@login_required
def search_user(request: HttpRequest) -> JsonResponse:
    """
    ✅ 기존 엔드포인트 호환용 alias
    (정식 구현은 search_api.search_users_for_api)
    """
    return JsonResponse(search_users_for_api(request))
