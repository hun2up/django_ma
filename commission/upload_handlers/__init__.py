# django_ma/commission/upload_handlers/__init__.py
from __future__ import annotations

"""
commission.upload_handlers public API

SSOT:
- _update_upload_log 는 deposit handler의 구현을 단일 진실로 사용한다.
"""

from .deposit import _update_upload_log  # SSOT: DepositUploadLog 갱신

# approval/efficiency handler들도 여기서 re-export (기존 코드 호환)
from .approval import _handle_upload_commission_approval  # noqa: F401
from .efficiency import _handle_upload_efficiency_pay_excess  # noqa: F401

__all__ = [
    "_update_upload_log",
    "_handle_upload_commission_approval",
    "_handle_upload_efficiency_pay_excess",
]
