# django_ma/commission/views/__init__.py
from __future__ import annotations

from importlib import import_module
from typing import Any


def _import_first(*module_paths: str):
    last_err: Exception | None = None
    for mp in module_paths:
        try:
            return import_module(mp)
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err
    raise ModuleNotFoundError("No module paths provided.")


def __getattr__(name: str) -> Any:
    # ---------------------------------------------------------------------
    # Pages (commission/urls.py에서 참조)
    # ---------------------------------------------------------------------
    if name in {"redirect_to_deposit", "deposit_home", "approval_home"}:
        mod = _import_first("commission.views.pages")
        return getattr(mod, name)

    # commission_home 은 legacy alias로 redirect_to_deposit과 동일 취급
    if name == "commission_home":
        mod = _import_first("commission.views.pages")
        return getattr(mod, "redirect_to_deposit")

    # ---------------------------------------------------------------------
    # Upload (채권)
    # ---------------------------------------------------------------------
    if name == "upload_excel":
        mod = _import_first("commission.views.api_upload")
        return getattr(mod, name)

    # ---------------------------------------------------------------------
    # Deposit APIs (채권 데이터 조회 + PDF + 사용자검색)
    # - ✅ 현재 repo에 존재하는 shim(api_deposit.py)만 SSOT로 사용
    # ---------------------------------------------------------------------
    if name in {
        "search_user",
        "api_user_detail",
        "api_deposit_summary",
        "api_deposit_surety_list",
        "api_deposit_other_list",
        "api_support_pdf",
    }:
        mod = _import_first("commission.views.api_deposit")
        return getattr(mod, name)

    # ---------------------------------------------------------------------
    # Approval/Efficiency upload
    # ---------------------------------------------------------------------
    if name in {"approval_upload_excel", "efficiency_upload_excel"}:
        mod = _import_first("commission.views.approval")
        return getattr(mod, name)

    # ---------------------------------------------------------------------
    # Downloads
    # ---------------------------------------------------------------------
    if name in {
        "download_upload_fail_excel",
        "download_approval_pending_excel",
        "download_efficiency_excess_excel",
    }:
        mod = _import_first("commission.views.downloads")
        return getattr(mod, name)

    raise AttributeError(f"module 'commission.views' has no attribute '{name}'")


__all__ = [
    # pages
    "redirect_to_deposit",
    "commission_home",
    "deposit_home",
    "approval_home",
    # upload
    "upload_excel",
    "approval_upload_excel",
    "efficiency_upload_excel",
    # deposit apis
    "search_user",
    "api_user_detail",
    "api_deposit_summary",
    "api_deposit_surety_list",
    "api_deposit_other_list",
    "api_support_pdf",
    # downloads
    "download_upload_fail_excel",
    "download_approval_pending_excel",
    "download_efficiency_excess_excel",
]
