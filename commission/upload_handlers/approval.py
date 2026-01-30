# django_ma/commission/upload_handlers/approval.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from accounts.models import CustomUser
from commission.models import ApprovalPending
from commission.upload_utils import _to_int, _norm_emp_id, _read_excel_raw_matrix


# =============================================================================
# ApprovalPending Upload
# =============================================================================

@dataclass
class _ApprovalRowSpec:
    idx_emp_name: int = 1   # B
    idx_user_id: int = 2    # C
    idx_pay: int = 13       # N (0-based)
    idx_flag: int = 14      # O


_SPEC = _ApprovalRowSpec()


def _safe_cell(row, idx: int) -> str:
    if len(row) <= idx:
        return ""
    v = row[idx]
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none") else s


def handle_upload_commission_approval(file_path: str, original_name: str, ym: str, part: str = ""):
    """
    수수료결재(kind=approval) 업로드

    조건:
    - N열(실지급액) > 0
    - O열(결재값) == 'N'
    - 동일 사번이 여러 행이면 실지급액 합산

    part:
    - 주어지면 해당 part 사용자만 저장(스코프 안전장치)
    """
    df = _read_excel_raw_matrix(file_path, original_name=original_name, skiprows=0, header_none=True)

    bucket: Dict[str, Dict[str, object]] = {}  # uid -> {emp_name:str, paid_sum:int}

    for _, row in df.iterrows():
        uid = _norm_emp_id(_safe_cell(row, _SPEC.idx_user_id))
        if not uid.isdigit():
            continue

        pay = _to_int(_safe_cell(row, _SPEC.idx_pay), default=0)
        flag = _safe_cell(row, _SPEC.idx_flag).upper()

        if pay <= 0 or flag != "N":
            continue

        emp_name = _safe_cell(row, _SPEC.idx_emp_name)

        rec = bucket.get(uid)
        if rec is None:
            bucket[uid] = {"emp_name": emp_name, "paid_sum": pay}
        else:
            if emp_name and not rec.get("emp_name"):
                rec["emp_name"] = emp_name
            rec["paid_sum"] = int(rec.get("paid_sum") or 0) + pay

    if not bucket:
        return {"inserted_or_updated": 0, "missing_users": 0, "missing_sample": []}

    qs = CustomUser.objects.filter(pk__in=bucket.keys())
    if part:
        qs = qs.filter(part=part)
    user_map = qs.in_bulk()

    missing = [uid for uid in bucket.keys() if uid not in user_map]
    missing_sample = missing[:10]

    objs: List[ApprovalPending] = []
    for uid, rec in bucket.items():
        u = user_map.get(uid)
        if not u:
            continue
        objs.append(
            ApprovalPending(
                ym=ym,
                user=u,
                emp_name=str(rec.get("emp_name") or ""),
                actual_pay=int(rec.get("paid_sum") or 0),
                approval_flag="N",
            )
        )

    if not objs:
        return {"inserted_or_updated": 0, "missing_users": len(missing), "missing_sample": missing_sample}

    ApprovalPending.objects.bulk_create(
        objs,
        batch_size=1000,
        update_conflicts=True,
        unique_fields=["ym", "user"],
        update_fields=["emp_name", "actual_pay", "approval_flag", "updated_at"],
    )

    return {
        "inserted_or_updated": len(objs),
        "missing_users": len(missing),
        "missing_sample": missing_sample,
    }


# Backward-compatible alias
_handle_upload_commission_approval = handle_upload_commission_approval
