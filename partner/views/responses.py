# partner/views/responses.py
# ------------------------------------------------------------
# ✅ 공용 JSON 응답/파서
# ------------------------------------------------------------

import json
from typing import Any, Dict, Optional

from django.http import JsonResponse


def json_ok(payload: Optional[Dict[str, Any]] = None, *, status: int = 200) -> JsonResponse:
    data: Dict[str, Any] = {"status": "success"}
    if payload:
        data.update(payload)
    return JsonResponse(data, status=status)


def json_err(message: str, *, status: int = 400, extra: Optional[Dict[str, Any]] = None) -> JsonResponse:
    data: Dict[str, Any] = {"status": "error", "message": message}
    if extra:
        data.update(extra)
    return JsonResponse(data, status=status)


def parse_json_body(request) -> Dict[str, Any]:
    """Safely parse JSON body; returns {} on any error."""
    try:
        raw = request.body or b"{}"
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw or "{}")
    except Exception:
        return {}
