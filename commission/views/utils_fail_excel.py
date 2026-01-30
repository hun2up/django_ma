# django_ma/commission/views/utils_fail_excel.py
from __future__ import annotations

import io
import uuid
from typing import Any

from django.core.cache import cache

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

FAIL_TTL_SECONDS = 60 * 60  # 1 hour


def store_fail_rows_as_excel(*, rows: list[dict[str, Any]], filename: str) -> str:
    """
    실패 rows를 xlsx로 만들어 cache에 저장하고 token 반환.

    rows 예:
      [{"user_id": "...", "reason": "...", ...}, ...]
    """
    if not rows:
        return ""

    if pd is None:
        # 현재 프로젝트는 pandas/openpyxl 사용 전제로 보이므로 빈 토큰 반환.
        return ""

    df = pd.DataFrame(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="fail_rows")

    token = uuid.uuid4().hex
    key = f"commission:upload_fail:{token}"
    cache.set(key, {"content": out.getvalue(), "filename": filename}, timeout=FAIL_TTL_SECONDS)
    return token


__all__ = ["store_fail_rows_as_excel", "FAIL_TTL_SECONDS"]
