# django_ma/accounts/services/users_excel_import.py
from __future__ import annotations

import math
from datetime import date
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd
from django.db import transaction

from accounts.models import CustomUser


REQUIRED_COLS = [
    "사원번호",
    "성명",
    "재직여부",
    "소속부서",
    "영업가족명",
    "입사일자(사원)",
    "퇴사일자(사원)",
]


def _to_str(v) -> str:
    return str(v or "").strip()


def _normalize_emp_id(v) -> str:
    """
    엑셀 '사원번호'가 float(2533454.0)로 들어오는 케이스 정규화
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    s = _to_str(v)
    # '2533454.0' -> '2533454'
    if s.endswith(".0"):
        s = s[:-2]
    # 혹시 과학표기법 등 대비
    try:
        if isinstance(v, (int,)) or (isinstance(v, float) and float(v).is_integer()):
            return str(int(float(v)))
    except Exception:
        pass
    return s


def _parse_date(v) -> Optional[date]:
    """
    pandas가 datetime/date/문자열 혼합으로 읽을 수 있어 안전하게 처리
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        ts = pd.to_datetime(v, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.date()
    except Exception:
        return None


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


@transaction.atomic
def import_users_from_sales_family_excel(
    file_path: str,
    *,
    protect_admin_grades: bool = True,
) -> Dict[str, Any]:
    """
    영업가족직원조회 엑셀을 규칙대로 CustomUser에 업서트.
    protect_admin_grades=True이면 기존 superuser/main_admin/sub_admin의 grade는 유지(권장 안전장치).
    """
    df = pd.read_excel(file_path, engine="openpyxl")

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

    created = updated = skipped = 0
    errors: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        emp_id = _normalize_emp_id(row.get("사원번호"))
        if not emp_id:
            skipped += 1
            continue

        name = _to_str(row.get("성명"))
        employed = _to_str(row.get("재직여부"))
        part = _to_str(row.get("소속부서"))
        branch = _to_str(row.get("영업가족명"))

        channel = _infer_channel(part)
        grade = _infer_grade(name, employed)
        status = _infer_status(grade)

        enter = _parse_date(row.get("입사일자(사원)"))
        quit_ = _parse_date(row.get("퇴사일자(사원)"))

        defaults = {
            "name": name or "",                 # 성명이 비어도 저장(grade inactive로 감)
            "channel": channel,
            "division": "",                     # ✅ 요청대로 빈값
            "part": part or "",
            "branch": branch or "",
            "grade": grade,
            "status": status,
            "enter": enter,
            "quit": quit_,
            "is_staff": False,                  # ✅ 전체 FALSE
            "is_active": True,                  # ✅ 전체 TRUE
        }

        try:
            obj = CustomUser.objects.filter(id=emp_id).first()

            # ✅ (권장) 관리자 계정 등급 보호: 엑셀로 basic/resign/inactive로 덮어쓰지 않게
            if obj and protect_admin_grades and obj.grade in ("superuser", "main_admin", "sub_admin"):
                # 관리자도 나머지 정보는 업데이트하고, grade/status만 유지하는 방식
                defaults.pop("grade", None)
                defaults.pop("status", None)

            if obj:
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save(update_fields=list(defaults.keys()))
                updated += 1
            else:
                CustomUser.objects.create(id=emp_id, **defaults)
                created += 1

        except Exception as e:
            errors.append({
                "row": int(idx) + 2,  # 엑셀 헤더 1줄 감안
                "id": emp_id,
                "name": name,
                "error": str(e),
            })

    return {
        "ok": len(errors) == 0,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }
