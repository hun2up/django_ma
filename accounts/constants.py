# django_ma/accounts/constants.py
"""
accounts 앱 공통 상수/헬퍼 모음
- 업로드 진행률/상태 캐시 키 규칙 단일화
"""

from __future__ import annotations


# ---------------------------------------------------------------------
# Upload progress cache keys (admin.py / views.py / tasks.py 공통)
# ---------------------------------------------------------------------
CACHE_PROGRESS_PREFIX = "upload_progress:"
CACHE_STATUS_PREFIX = "upload_status:"
CACHE_ERROR_PREFIX = "upload_error:"
CACHE_RESULT_PATH_PREFIX = "upload_result_path:"

CACHE_TIMEOUT_SECONDS = 60 * 60  # 1 hour


def cache_key(prefix: str, task_id: str) -> str:
    return f"{prefix}{task_id}"


# ---------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------
EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
