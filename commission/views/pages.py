# django_ma/commission/views/pages.py
from __future__ import annotations

from django.shortcuts import redirect, render

from accounts.decorators import grade_required
from accounts.models import CustomUser

from commission.views.constants import UPLOAD_CATEGORIES, SUPPORTED_UPLOAD_TYPES
from commission.upload_handlers.registry import supported_upload_types
from commission.models import DepositUploadLog
from commission.upload_handlers.registry import supported_upload_types


UPLOAD_TYPES_ORDER = [
    "최종지급액",
    "환수지급예상",
    "보증증액",
    "보증보험",
    "기타채권",
    "통산생보",
    "통산손보",
    "응당생보",
    "응당손보",
]


def redirect_to_deposit(request):
    return redirect("commission:deposit_home")


@grade_required("staff", "admin", "superuser")
def deposit_home(request):
    # 1) 행: 현재 등록 유저들의 part 목록
    parts = (
        CustomUser.objects
        .exclude(part__isnull=True)
        .exclude(part__exact="")
        .exclude(part__icontains="센터")   # ✅ 추가
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )
    parts = list(parts)

    # 2) 열: 업로드 구분 목록 (고정 순서)
    #   - registry 기반으로 하고 싶으면 supported_upload_types()를 쓰되, 순서 유지를 위해 ORDER를 권장
    supported = set(supported_upload_types())
    upload_types = [x for x in UPLOAD_TYPES_ORDER if x in supported]
    # 혹시 registry에 없는 항목도 보여야 한다면 위 필터를 제거하세요:
    # upload_types = UPLOAD_TYPES_ORDER

    # 3) 셀 데이터: (part, upload_type) -> uploaded_at
    logs = (
        DepositUploadLog.objects
        .filter(part__in=parts, upload_type__in=upload_types)
        .only("part", "upload_type", "uploaded_at")
    )

    # upload_dates[part][upload_type] = "YYYY-MM-DD HH:MM"
    upload_dates = {p: {} for p in parts}
    for row in logs:
        ts = getattr(row, "uploaded_at", None)
        upload_dates[row.part][row.upload_type] = ts.strftime("%Y-%m-%d") if ts else "-"

    # 빈 셀도 "-"로 채우고 싶으면:
    for p in parts:
        for ut in upload_types:
            upload_dates[p].setdefault(ut, "-")

    ctx = {
        "parts": parts,                 # 열 (부서목록)
        "upload_types": upload_types,   # 행 (업로드구분)
        "upload_dates": upload_dates,   # dict[part][upload_type] = date str
        "supported_upload_types": upload_types,  # 템플릿에서 data-upload-date 부여용
        # 기존 deposit_home이 쓰는 다른 ctx들도 그대로 유지
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
