# django_ma/commission/upload_handlers/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Literal

from . import deposit

Mode = Literal["df", "file"]


@dataclass(frozen=True)
class UploadSpec:
    """
    SSOT 업로드 스펙
    - mode == "df"   : read_excel_safely -> DataFrame -> fn(df)
    - mode == "file" : FileSystemStorage 저장 경로 -> fn(file_path, original_name)
    """
    upload_type: str
    mode: Mode
    fn: Callable
    msg_tpl: str


# ---------------------------------------------------------------------
# SSOT Registry
# ---------------------------------------------------------------------
_REGISTRY: Dict[str, UploadSpec] = {
    # DataFrame handlers
    "최종지급액": UploadSpec(
        upload_type="최종지급액",
        mode="df",
        fn=deposit.handle_upload_final_payment,
        msg_tpl="✅ 최종지급액 업로드 완료 ({n}건)",
    ),
    "환수지급예상": UploadSpec(
        upload_type="환수지급예상",
        mode="df",
        fn=deposit.handle_upload_refund_pay_expected,
        msg_tpl="✅ 환수/지급예상 업로드 완료 ({n}건)",
    ),

    # 기존 보증증액(호환 유지) → 내부적으로 채권지표 로직과 동일
    "보증증액": UploadSpec(
        upload_type="보증증액",
        mode="df",
        fn=deposit.handle_upload_guarantee_increase,
        msg_tpl="✅ 보증증액 업로드 완료 ({n}건)",
    ),

    # ✅ 신규: 채권지표
    "채권지표": UploadSpec(
        upload_type="채권지표",
        mode="df",
        fn=deposit.handle_upload_deposit_metrics,
        msg_tpl="✅ 채권지표 업로드 완료 ({n}건)",
    ),

    "응당생보": UploadSpec(
        upload_type="응당생보",
        mode="df",
        fn=deposit.handle_upload_ls_due,
        msg_tpl="✅ 응당생보 업로드 완료 ({n}건)",
    ),
    "응당손보": UploadSpec(
        upload_type="응당손보",
        mode="df",
        fn=deposit.handle_upload_ns_due,
        msg_tpl="✅ 응당손보 업로드 완료 ({n}건)",
    ),
    "보증보험": UploadSpec(
        upload_type="보증보험",
        mode="df",
        fn=deposit.handle_upload_surety,
        msg_tpl="✅ 보증보험 업로드 완료 ({n}건)",
    ),
    "기타채권": UploadSpec(
        upload_type="기타채권",
        mode="df",
        fn=deposit.handle_upload_other_debt,
        msg_tpl="✅ 기타채권 업로드 완료 ({n}건)",
    ),

    # Raw matrix file handlers
    "통산손보": UploadSpec(
        upload_type="통산손보",
        mode="file",
        fn=deposit.handle_upload_ns_total_from_file,
        msg_tpl="✅ 통산손보 업로드 완료 ({n}건)",
    ),
    "통산생보": UploadSpec(
        upload_type="통산생보",
        mode="file",
        fn=deposit.handle_upload_ls_total_from_file,
        msg_tpl="✅ 통산생보 업로드 완료 ({n}건)",
    ),
}


def get_upload_spec(upload_type: str) -> UploadSpec:
    try:
        return _REGISTRY[upload_type]
    except KeyError:
        raise KeyError(f"Unsupported upload_type: {upload_type}")


def supported_upload_types() -> Iterable[str]:
    return tuple(_REGISTRY.keys())


__all__ = ["UploadSpec", "get_upload_spec", "supported_upload_types"]
