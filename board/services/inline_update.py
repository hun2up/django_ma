# django_ma/board/services/inline_update.py
# =========================================================
# Inline Update Service
# - Post/Task 공용: handler/status 인라인 변경
# - JSON 응답 형식 유지 (프런트 JS 영향 최소화)
# =========================================================

from __future__ import annotations

from typing import List

from django.http import JsonResponse
from django.utils import timezone


def inline_update_common(*, obj, action: str, value: str, allowed_status_values: List[str]) -> JsonResponse:
    """
    ✅ 인라인 담당자/상태 업데이트 공용 처리(Post/Task 공용)
    - action: handler | status
    """
    now = timezone.localtime()

    # ---------------------------------------------------------
    # ✅ 담당자 변경
    # ---------------------------------------------------------
    if action == "handler":
        obj.handler = "" if value in ("", "선택") else value
        obj.status_updated_at = now
        obj.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{obj.handler or '미지정'}'로 변경되었습니다.",
            "handler": obj.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    # ---------------------------------------------------------
    # ✅ 상태 변경
    # ---------------------------------------------------------
    if value not in allowed_status_values:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    obj.status = value
    obj.status_updated_at = now
    obj.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{obj.status}'로 변경되었습니다.",
        "status": obj.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })
