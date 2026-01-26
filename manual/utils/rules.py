# django_ma/manual/utils/rules.py

from __future__ import annotations

from typing import Tuple

from manual.models import Manual, ManualSection


def ensure_default_section(manual: Manual) -> ManualSection:
    """
    ✅ 섹션이 하나도 없을 경우 기본 섹션 1개 생성
    - 상세 화면이 완전히 비어버리는 상황 방지
    """
    first = manual.sections.order_by("sort_order", "id").first()
    if first:
        return first
    return ManualSection.objects.create(manual=manual, sort_order=1, title="")


def access_to_flags(access: str) -> Tuple[bool, bool]:
    """
    access 문자열(normal/admin/staff) -> (admin_only, is_published)

    - normal: (False, True)
    - admin : (True,  True)
    - staff : (False, False)  # 직원전용=비공개
    """
    if access == "admin":
        return True, True
    if access == "staff":
        return False, False
    return False, True
