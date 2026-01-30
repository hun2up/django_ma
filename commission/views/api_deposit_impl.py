# django_ma/commission/views/api_deposit_impl.py
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

# TODO: 기존 구현이 있다면 여기로 옮기세요.
# from commission.models import DepositSummary, DepositSurety, DepositOther
# from accounts.search_api import search_users (또는 너 SSOT search_user API)


@require_GET
def search_user(request):
    return JsonResponse({"ok": True, "results": []})


@require_GET
def api_user_detail(request):
    return JsonResponse({"ok": True, "data": {}})


@require_GET
def api_deposit_summary(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_deposit_surety_list(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_deposit_other_list(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_support_pdf(request):
    return JsonResponse({"ok": False, "message": "Not implemented"}, status=501)
