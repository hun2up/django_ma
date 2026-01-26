# django_ma/partner/views/context.py
# ------------------------------------------------------------
# ✅ 페이지 공용 컨텍스트 빌더
# - manage_charts/manage_rate/manage_calculate 등에서 동일 패턴 사용
# ------------------------------------------------------------

from typing import Any, Dict, Optional

from django.shortcuts import render
from django.urls import reverse

from accounts.models import CustomUser
from .utils import build_current_user_payload, get_now_ym


def build_manage_context(
    *,
    request,
    page_kind: str,
    template_name: str,
    fetch_name: str,
    save_name: str,
    delete_name: str,
    update_process_name: str,
    boot_key: str,
    extra_context: Optional[Dict[str, Any]] = None,
):
    y, m = get_now_ym()
    user: CustomUser = request.user

    data_fetch_url = reverse(fetch_name)
    data_save_url = reverse(save_name)
    data_delete_url = reverse(delete_name)
    update_process_date_url = reverse(update_process_name)

    boot = {
        "userGrade": getattr(user, "grade", ""),
        "currentYear": y,
        "currentMonth": m,
        "selectedYear": y,
        "selectedMonth": m,
        # 기존 정책: head/leader 자동조회
        "autoLoad": getattr(user, "grade", "") in ["head", "leader"],
        "dataFetchUrl": data_fetch_url,
        "dataSaveUrl": data_save_url,
        "dataDeleteUrl": data_delete_url,
        "updateProcessDateUrl": update_process_date_url,
        "kind": page_kind,
    }

    ctx: Dict[str, Any] = {
        "current_year": y,
        "current_month": m,
        "selected_year": y,
        "selected_month": m,
        "auto_load": True,
        "data_fetch_url": data_fetch_url,
        "data_save_url": data_save_url,
        "data_delete_url": data_delete_url,
        "update_process_date_url": update_process_date_url,
        boot_key: boot,
        "currentUser": build_current_user_payload(user),
    }
    if extra_context:
        ctx.update(extra_context)
    return render(request, template_name, ctx)
