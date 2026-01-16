# django_ma/manual/utils.py

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from django.http import JsonResponse
from django.shortcuts import render

from .models import Manual, ManualBlock, ManualBlockAttachment, ManualSection


# -----------------------------------------------------------------------------
# Basic parsing helpers
# -----------------------------------------------------------------------------

def to_str(v: Any) -> str:
    """None/공백 입력을 안전하게 문자열로 정규화"""
    return str(v or "").strip()


def is_digits(v: Any) -> bool:
    """int로 변환 가능한 숫자 문자열인지 체크"""
    return str(v or "").isdigit()


def json_body(request) -> Dict[str, Any]:
    """
    request.body(JSON)를 안전하게 dict로 파싱
    - 파싱 실패/빈 바디: {}
    """
    try:
        return json.loads((request.body or b"").decode("utf-8"))
    except Exception:
        return {}


# -----------------------------------------------------------------------------
# Unified responses
# -----------------------------------------------------------------------------

def ok(data: Optional[dict] = None) -> JsonResponse:
    payload = {"ok": True}
    if isinstance(data, dict):
        payload.update(data)
    return JsonResponse(payload)


def fail(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "message": message}, status=status)


# -----------------------------------------------------------------------------
# Permission helpers
# -----------------------------------------------------------------------------

def is_superuser(user) -> bool:
    """grade 기반 superuser 판정(프로젝트 컨벤션 유지)"""
    return getattr(user, "grade", "") == "superuser"


def ensure_superuser_or_403(request) -> Optional[JsonResponse]:
    """
    ✅ superuser가 아니면 즉시 403 반환용 헬퍼
    - 각 AJAX에서 동일 패턴 반복을 줄이기 위함
    """
    if not is_superuser(request.user):
        return fail("권한이 없습니다.", 403)
    return None


def manual_accessible_or_denied(request, manual: Manual):
    """
    ✅ 매뉴얼 접근 권한 체크

    - admin_only=True   : superuser/main_admin만 접근
    - is_published=False: superuser만 접근

    반환:
    - 접근 가능: None
    - 접근 불가: no_permission_popup.html 렌더 결과
    """
    grade = getattr(request.user, "grade", "")

    if manual.admin_only and grade not in ("superuser", "main_admin"):
        return render(request, "no_permission_popup.html")

    if (not manual.is_published) and grade != "superuser":
        return render(request, "no_permission_popup.html")

    return None


# -----------------------------------------------------------------------------
# Business rules helpers
# -----------------------------------------------------------------------------

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
    access 문자열(normal/admin/staff) -> (admin_only, is_published) 변환

    - normal: (False, True)
    - admin : (True,  True)
    - staff : (False, False)  # 직원전용=비공개
    """
    if access == "admin":
        return True, True
    if access == "staff":
        return False, False
    return False, True


# -----------------------------------------------------------------------------
# Serialization helpers (front-end immediate render)
# -----------------------------------------------------------------------------

def attachment_to_dict(a: ManualBlockAttachment) -> dict:
    return {
        "id": a.id,
        "name": a.original_name or os.path.basename(a.file.name),
        "url": a.file.url if a.file else "",
        "size": a.size or 0,
    }


def block_to_dict(b: ManualBlock) -> dict:
    """
    블록을 프런트가 즉시 DOM 업데이트 가능한 dict로 변환
    - 이미지 + 첨부파일 포함
    """
    return {
        "id": b.id,
        "section_id": b.section_id,
        "content": b.content,
        "image_url": b.image.url if b.image else "",
        "attachments": [
            attachment_to_dict(a)
            for a in b.attachments.all().order_by("created_at", "id")
        ],
    }
