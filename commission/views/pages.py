# django_ma/commission/views/pages.py
from __future__ import annotations

from django.shortcuts import redirect, render

from accounts.decorators import grade_required
from commission.views.constants import UPLOAD_CATEGORIES, SUPPORTED_UPLOAD_TYPES
from commission.upload_handlers.registry import supported_upload_types
from commission.models import DepositUploadLog


def redirect_to_deposit(request):
    return redirect("commission:deposit_home")


@grade_required("staff", "admin", "superuser")
def deposit_home(request):
    # 사업부 목록이 어디서 오느냐에 따라 다름 (예: partner/constants.py BRANCH_PARTS 같은 SSOT)
    # 일단 "parts"는 템플릿이 기대하는 key로 내려줘야 합니다.
    parts = sorted(set([p for p in DepositUploadLog.objects.values_list("part", flat=True) if p]))

    logs = (
        DepositUploadLog.objects
        .all()
        .order_by("part", "upload_type")
    )

    ctx = {
        "parts": parts,
        "upload_categories": UPLOAD_CATEGORIES,
        "supported_upload_types": sorted(SUPPORTED_UPLOAD_TYPES or supported_upload_types()),
        "upload_logs": logs,
    }
    return render(request, "commission/deposit_home.html", ctx)


@grade_required("staff", "admin", "superuser")
def approval_home(request):
    return render(request, "commission/approval_home.html")


@grade_required("staff", "admin", "superuser")
def support_home(request):
    """
    support 페이지가 별도로 존재한다면 템플릿을 연결.
    템플릿이 없다면(운영중 미사용) deposit으로 보내도 안전.
    """
    # 실제 템플릿이 생기면 아래로 교체:
    # return render(request, "commission/support_home.html")
    return redirect("commission:deposit_home")
