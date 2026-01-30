# django_ma/commission/views/utils_json.py
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

from django.http import HttpResponse, JsonResponse


def _json_error(message: str, status: int = 400, **extra: Any) -> JsonResponse:
    payload: dict[str, Any] = {"ok": False, "message": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _json_ok(message: str | None = None, **extra: Any) -> JsonResponse:
    payload: dict[str, Any] = {"ok": True}
    if message is not None:
        payload["message"] = message
    payload.update(extra)
    return JsonResponse(payload)


def _set_attachment_filename(resp: HttpResponse, filename: str) -> HttpResponse:
    """
    한글 파일명도 안정적으로 저장되도록
    filename + filename* (RFC5987) 동시 세팅
    """
    ascii_fallback = re.sub(r"[^\x20-\x7E]", "_", filename)
    quoted = quote(filename)

    resp["Content-Disposition"] = (
        f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted}'
    )
    return resp


__all__ = ["_json_error", "_json_ok", "_set_attachment_filename"]
