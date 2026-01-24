# django_ma/accounts/services/users_excel_import.py
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
from django.db import transaction

from accounts.models import CustomUser


# =============================================================================
# Required Excel Columns
# =============================================================================

REQUIRED_COLS = [
    "사원번호",
    "성명",
    "재직여부",
    "소속부서",
    "영업가족명",
    "입사일자(사원)",
    "퇴사일자(사원)",
]

ADMIN_GRADES = {"superuser", "main_admin", "sub_admin"}


# =============================================================================
# Parsing helpers
# =============================================================================

def _to_str(v) -> str:
    return str(v or "").strip()


def _is_nan(v) -> bool:
    return isinstance(v, float) and math.isnan(v)


def _normalize_emp_id(v) -> str:
    """
    엑셀 사원번호가 float(2533454.0)로 들어오는 케이스 정규화.
    과학표기법/float 정수형도 최대한 안전하게 정규화.
    """
    if v is None or _is_nan(v):
        return ""

    # pandas가 숫자로 읽는 경우가 많아 먼저 숫자 케이스 처리
    try:
        if isinstance(v, (int,)):
            return str(v)
        if isinstance(v, float) and float(v).is_integer():
            return str(int(v))
    except Exception:
        pass

    s = _to_str(v)
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _parse_date(v) -> Optional[date]:
    """
    pandas가 datetime/date/문자열 혼합으로 읽을 수 있어 안전하게 처리
    """
    if v is None or _is_nan(v):
        return None
    try:
        ts = pd.to_datetime(v, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


# =============================================================================
# Business rules (channel / grade / status)
# =============================================================================

def _infer_channel(part_text: str) -> str:
    """
    규칙 1. 부문 설정
    - 소속부서에 'MA' 포함 => 'MA부문'
    - 'CA' 포함 => 'CA부문'
    - 'PA' 포함 => 'PA부문'
    - else => '전략부문'
    """
    t = _to_str(part_text).upper()
    if "MA" in t:
        return "MA부문"
    if "CA" in t:
        return "CA부문"
    if "PA" in t:
        return "PA부문"
    return "전략부문"


def _infer_grade(name: str, employed_flag: str) -> str:
    """
    규칙 2. 권한 설정
    - 기본 basic
    - 재직여부 == '퇴사' => resign
    - 성명 없음 OR 성명에 '*' 포함 => inactive
    ✅ 우선순위: inactive가 가장 강함(결측/마스킹 계정은 무조건 inactive)
    """
    n = _to_str(name)
    r = _to_str(employed_flag)
    if (not n) or ("*" in n):
        return "inactive"
    if r == "퇴사":
        return "resign"
    return "basic"


def _infer_status(grade: str) -> str:
    """
    규칙 3. 상태 설정
    - grade == basic => '재직'
    - else(resign/inactive) => '퇴사'
    """
    return "재직" if grade == "basic" else "퇴사"


# =============================================================================
# Row normalization
# =============================================================================

@dataclass(frozen=True)
class ExcelUserRow:
    emp_id: str
    name: str
    employed: str
    part: str
    branch: str
    enter: Optional[date]
    quit: Optional[date]


def _row_to_user_row(row: pd.Series) -> ExcelUserRow:
    emp_id = _normalize_emp_id(row.get("사원번호"))
    name = _to_str(row.get("성명"))
    employed = _to_str(row.get("재직여부"))
    part = _to_str(row.get("소속부서"))
    branch = _to_str(row.get("영업가족명"))
    enter = _parse_date(row.get("입사일자(사원)"))
    quit_ = _parse_date(row.get("퇴사일자(사원)"))

    return ExcelUserRow(
        emp_id=emp_id,
        name=name,
        employed=employed,
        part=part,
        branch=branch,
        enter=enter,
        quit=quit_,
    )


def _build_defaults(u: ExcelUserRow) -> Dict[str, Any]:
    channel = _infer_channel(u.part)
    grade = _infer_grade(u.name, u.employed)
    status = _infer_status(grade)

    # ✅ 요구사항 유지: division 빈값, is_staff=False, is_active=True 강제
    return {
        "name": u.name or "",      # 비어도 저장(grade inactive)
        "channel": channel,
        "division": "",
        "part": u.part or "",
        "branch": u.branch or "",
        "grade": grade,
        "status": status,
        "enter": u.enter,
        "quit": u.quit,
        "is_staff": False,
        "is_active": True,
    }


# =============================================================================
# Public service
# =============================================================================

@transaction.atomic
def import_users_from_sales_family_excel(
    file_path: str,
    *,
    protect_admin_grades: bool = True,
) -> Dict[str, Any]:
    """
    영업가족직원조회 엑셀을 규칙대로 CustomUser에 업서트.

    Args:
      file_path: 업로드된 엑셀 파일 경로
      protect_admin_grades:
        - True이면 기존 superuser/main_admin/sub_admin의 grade/status는 엑셀로 덮어쓰지 않음(권장)

    Returns:
      {
        "ok": bool,
        "error": str|None,
        "created": int,
        "updated": int,
        "skipped": int,
        "errors": [ {row,id,name,error}, ... ]
      }
    """
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        return {
            "ok": False,
            "error": f"엑셀 읽기 실패: {e}",
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return {
            "ok": False,
            "error": f"필수 컬럼 누락: {', '.join(missing)}",
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    created = 0
    updated = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    # iterrows는 느릴 수 있지만, 업서트/규칙 적용이 행 단위라 안정성이 좋음(현 구조 유지)
    for idx, row in df.iterrows():
        user_row = _row_to_user_row(row)

        if not user_row.emp_id:
            skipped += 1
            continue

        defaults = _build_defaults(user_row)

        try:
            obj = CustomUser.objects.filter(id=user_row.emp_id).first()

            # ✅ 관리자 계정 등급/상태 보호 (grade/status만 유지)
            if obj and protect_admin_grades and obj.grade in ADMIN_GRADES:
                defaults.pop("grade", None)
                defaults.pop("status", None)

            if obj:
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save(update_fields=list(defaults.keys()))
                updated += 1
            else:
                CustomUser.objects.create(id=user_row.emp_id, **defaults)
                created += 1

        except Exception as e:
            errors.append(
                {
                    "row": int(idx) + 2,  # 엑셀 헤더 1줄 감안
                    "id": user_row.emp_id,
                    "name": user_row.name,
                    "error": str(e),
                }
            )

    return {
        "ok": len(errors) == 0,
        "error": "" if len(errors) == 0 else "일부 행 처리 중 오류가 발생했습니다.",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }
