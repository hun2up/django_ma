# django_ma/manual/utils/permissions.py

from __future__ import annotations

from typing import Optional

from django.shortcuts import render

from manual.models import Manual
from .http import fail


def user_grade(user) -> str:
    """프로젝트 컨벤션: CustomUser.grade 기반 권한"""
    return getattr(user, "grade", "") or ""


def is_superuser(user) -> bool:
    return user_grade(user) == "superuser"


def is_head(user) -> bool:
    return user_grade(user) == "head"


def ensure_superuser_or_403(request) -> Optional[object]:
    """
    ✅ superuser가 아니면 즉시 403(JsonResponse) 반환
    - views에서 `resp = ensure_superuser_or_403(request); if resp: return resp` 패턴으로 사용
    """
    if not is_superuser(request.user):
        return fail("권한이 없습니다.", 403)
    return None


def filter_manuals_for_user(qs, user):
    """
    ✅ 목록 노출 정책(SSOT)
    - 직원전용(is_published=False): superuser만 노출
    - 관리자전용(admin_only=True): superuser/head만 노출
    """
    grade = user_grade(user)

    # 직원전용(비공개)은 superuser만
    if grade != "superuser":
        qs = qs.filter(is_published=True)

    # 관리자전용은 superuser/head만
    if grade not in ("superuser", "head"):
        qs = qs.filter(admin_only=False)

    return qs


def manual_accessible_or_denied(request, manual: Manual):
    """
    ✅ 매뉴얼 접근 권한 체크

    규칙:
    - admin_only=True     : superuser/head만 접근
    - is_published=False  : superuser만 접근

    반환:
    - 접근 가능: None
    - 접근 불가: no_permission_popup.html 렌더 결과
    """
    grade = user_grade(request.user)

    if manual.admin_only and grade not in ("superuser", "head"):
        return render(request, "no_permission_popup.html")

    if (not manual.is_published) and grade != "superuser":
        return render(request, "no_permission_popup.html")

    return None
