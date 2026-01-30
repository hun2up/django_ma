# django_ma/commission/views/utils_excel.py
from __future__ import annotations

"""
Backward-compatible shim.

과거: commission.views.utils_excel 에 엑셀 유틸이 있었음
현재: commission.upload_utils 로 이동(또는 이동 예정)

기존 import 경로를 유지하는 코드가 있어도 ImportError가 나지 않도록
얇게 re-export 한다.
"""

from commission.upload_utils import (  # noqa: F401
    _read_excel_safely,
    _read_excel_raw_matrix,
    _detect_col,
    _find_exact_or_space_removed,
    _detect_emp_id_col,
    _detect_refundpay_col,
    _to_int,
    _to_decimal,
    _to_date,
    _to_div,
    _norm_emp_id,
    _safe_decimal_q2,
    _extract_emp7_from_a,
    _bulk_existing_user_ids,
)

__all__ = [
    "_read_excel_safely",
    "_read_excel_raw_matrix",
    "_detect_col",
    "_find_exact_or_space_removed",
    "_detect_emp_id_col",
    "_detect_refundpay_col",
    "_to_int",
    "_to_decimal",
    "_to_date",
    "_to_div",
    "_norm_emp_id",
    "_safe_decimal_q2",
    "_extract_emp7_from_a",
    "_bulk_existing_user_ids",
]
