# django_ma/commission/views/api_deposit.py
from __future__ import annotations

"""
Backward-compatible shim.

- 기본 구현은 commission.views.api.deposit (패키지 분리 버전)
- 하지만 현재 repo에 그 파일이 없을 수 있으니,
  단일 구현(commission.views.api_deposit_impl)을 fallback으로 둔다.
"""

from importlib import import_module


def _import_impl():
    # 1) 패키지 분리 구조가 있으면 그걸 사용
    try:
        return import_module("commission.views.api.deposit")
    except Exception:
        # 2) 없으면 단일 모듈(아래에서 만들 파일) 사용
        return import_module("commission.views.api_deposit_impl")


_impl = _import_impl()

search_user = getattr(_impl, "search_user")
api_user_detail = getattr(_impl, "api_user_detail")
api_deposit_summary = getattr(_impl, "api_deposit_summary")
api_deposit_surety_list = getattr(_impl, "api_deposit_surety_list")
api_deposit_other_list = getattr(_impl, "api_deposit_other_list")
api_support_pdf = getattr(_impl, "api_support_pdf")

__all__ = [
    "search_user",
    "api_user_detail",
    "api_deposit_summary",
    "api_deposit_surety_list",
    "api_deposit_other_list",
    "api_support_pdf",
]
