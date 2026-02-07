# django_ma/board/views/forms.py
# =========================================================
# Form / PDF / Search Views
# - support_form / states_form
# - search_user
# - generate_request_support / generate_request_states
# =========================================================

from __future__ import annotations

from typing import Any, Dict, List

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from accounts.decorators import grade_required
from accounts.search_api import search_users_for_api

from ..constants import (
    BOARD_ALLOWED_GRADES,
    SUPPORT_FORM, STATES_FORM,
    SUPPORT_TARGET_FIELDS, SUPPORT_CONTRACT_FIELDS,
)
from ..policies import is_inactive
from board.utils import generate_request_support as build_support
from board.utils import generate_request_states as build_states


__all__ = [
    "support_form",
    "states_form",
    "generate_request_support",
    "generate_request_states",
    "search_user",
]


# ---------------------------------------------------------
# ✅ SSOT: support/states form context
# ---------------------------------------------------------
def build_support_form_context() -> Dict[str, Any]:
    """
    support_form / states_form 공용 컨텍스트(SSOT)
    - templates expected: fields, contracts
    """
    return {
        "fields": SUPPORT_TARGET_FIELDS,
        "contracts": SUPPORT_CONTRACT_FIELDS,
        # ✅ 템플릿에서 "not in 문자열" 오용 방지용
        #    (support_form에서 권한 안내/방어적 표기)
        "grades_allowed": list(BOARD_ALLOWED_GRADES),
    }


# ---------------------------------------------------------
# ✅ Support / States Form
# ---------------------------------------------------------
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def support_form(request: HttpRequest) -> HttpResponse:
    """업무요청서 작성 페이지 (superuser/head/leader)"""
    return render(request, "board/support_form.html", build_support_form_context())


@login_required
def states_form(request: HttpRequest) -> HttpResponse:
    """FA소명서 작성 페이지 (inactive 외 모두)"""
    if is_inactive(request.user):
        messages.error(request, "접근 권한이 없습니다.")
        return redirect("home")
    return render(request, "board/states_form.html", build_support_form_context())


# ---------------------------------------------------------
# ✅ Search User (Legacy alias 유지)
# ---------------------------------------------------------
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def search_user(request: HttpRequest) -> JsonResponse:
    """
    Legacy alias: /board/search-user/
    실제 구현은 accounts.search_api.search_users_for_api(SSOT)
    """
    return JsonResponse(search_users_for_api(request))


# ---------------------------------------------------------
# ✅ PDF Generate
# ---------------------------------------------------------
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def generate_request_support(request: HttpRequest) -> HttpResponse:
    """업무요청서 PDF (superuser/head/leader)"""
    pdf_response = build_support(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect(SUPPORT_FORM)
    return pdf_response


@login_required
@require_POST
def generate_request_states(request: HttpRequest) -> HttpResponse:
    """FA소명서 PDF (inactive 외 모두)"""
    if is_inactive(request.user):
        # ✅ fetch(AJAX)로 호출되는 경우: JSON 에러로 명확히 반환
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "message": "접근 권한이 없습니다."}, status=403)
        messages.error(request, "접근 권한이 없습니다.")
        return redirect("home")


    pdf_response = build_states(request)
    if pdf_response is None:
        # ✅ fetch(AJAX)로 호출되는 경우: JSON 에러로 명확히 반환
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "message": "PDF 생성 중 오류가 발생했습니다."}, status=400)
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect(STATES_FORM)
    return pdf_response
