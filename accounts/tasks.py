# django_ma/accounts/tasks.py

from __future__ import annotations

import math
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from .models import CustomUser

import logging
logger = logging.getLogger(__name__)

# =============================================================================
# 0) 업로드 엑셀 규격/정책 상수
# =============================================================================
EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ✅ 영업가족직원조회 엑셀 필수 컬럼 (요청 명세)
REQUIRED_COLS = [
    "사원번호",
    "성명",
    "재직여부",
    "소속부서",
    "영업가족명",
    "입사일자(사원)",
    "퇴사일자(사원)",
]

# ✅ 관리자 보호(권장): 기존 이 등급은 엑셀로 grade 강등하지 않음
PROTECTED_GRADES = {"superuser", "main_admin", "sub_admin"}

# 결과 리포트 엑셀 시트명
RESULT_SHEET_NAME = "UploadResult"


# =============================================================================
# 1) 공용 유틸
# =============================================================================
def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()


def _normalize_emp_id(v) -> str:
    """
    엑셀 '사원번호'가 float(2533454.0)로 들어오는 케이스 정규화
    """
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""

    s = _to_str(v)
    if not s:
        return ""

    # '2533454.0' -> '2533454'
    if s.endswith(".0"):
        s = s[:-2]

    # 과학표기/소수점 혼입 방어
    try:
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float) and float(v).is_integer():
            return str(int(v))
    except Exception:
        pass

    return s


def parse_date(value) -> Optional[date]:
    """
    엑셀 날짜가 datetime/date/문자열 혼합으로 올 수 있어 안전 변환
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = _to_str(value)
    if not s:
        return None

    # 1) yyyy-mm-dd
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


# =============================================================================
# 2) 요청 규칙(부문/권한/상태) 계산
# =============================================================================
def _infer_channel(part_text: str) -> str:
    """
    규칙 1. 부문 설정
      - 소속부서에 'MA' 포함 -> 'MA부문'
      - 'CA' 포함 -> 'CA부문'
      - 'PA' 포함 -> 'PA부문'
      - else -> '전략부문'
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
      - 기본값: basic
      - 재직여부 == '퇴사' -> resign
      - 성명 없거나 OR 성명에 '*' 포함 -> inactive
    ✅ 우선순위: inactive 최상(결측/마스킹 계정은 무조건 inactive)
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
      - grade == basic -> '재직'
      - resign/inactive -> '퇴사'
    """
    return "재직" if grade == "basic" else "퇴사"


# =============================================================================
# 3) 진행률/결과 파일 cache 키
# =============================================================================
def _cache_keys(task_id: str) -> Dict[str, str]:
    return {
        "percent": f"upload_progress:{task_id}",
        "status": f"upload_status:{task_id}",
        "error": f"upload_error:{task_id}",
        "result_path": f"upload_result_path:{task_id}",
    }


# =============================================================================
# 4) 엑셀 시트 선택 로직 (시트명 무관)
#    - "필수 컬럼이 모두 존재하는 첫 시트"를 자동 선택
# =============================================================================
def _read_header(ws) -> list[str]:
    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header:
        return []
    return [_to_str(v) for v in header]

def _pick_worksheet_by_required_cols(wb):
    for name in wb.sheetnames:
        ws = wb[name]
        if ws.sheet_state in ("hidden", "veryHidden"):
            continue

        headers = _read_header(ws)
        header_set = set(headers)
        if all(c in header_set for c in REQUIRED_COLS):
            return name, ws, headers

    visible = []
    for name in wb.sheetnames:
        ws = wb[name]
        if ws.sheet_state in ("hidden", "veryHidden"):
            continue
        headers = _read_header(ws)
        visible.append((name, headers[:20]))

    raise ValueError(
        "필수 컬럼을 포함한 업로드 시트를 찾을 수 없습니다. "
        f"(필수: {REQUIRED_COLS}) / 시트 목록: {wb.sheetnames} / "
        f"표시 시트 헤더(앞 20개): {visible}"
    )


# =============================================================================
# 5) 결과 리포트 엑셀 생성
# =============================================================================
def _make_result_wb(
    results: List[List[Any]],
    total: int,
    new_cnt: int,
    upd_cnt: int,
    skip_cnt: int,
    err_cnt: int,
    picked_sheet: str,
) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = RESULT_SHEET_NAME

    ws.append(["Row", "사원번호", "성명", "부문", "부서", "지점", "권한(grade)", "상태", "Result"])

    fill_new = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_update = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    fill_skip = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    fill_error = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row in results:
        ws.append(row)
        r = ws.max_row
        t = _to_str(row[-1])
        cell = ws[f"I{r}"]
        if "🟢" in t:
            cell.fill = fill_new
        elif "✅" in t:
            cell.fill = fill_update
        elif "⚠️" in t:
            cell.fill = fill_skip
        elif "❌" in t:
            cell.fill = fill_error

    ws.append([])
    ws.append(["선택된 시트", picked_sheet])
    ws.append(["총 데이터(행)", total])
    ws.append(["신규 추가", new_cnt])
    ws.append(["업데이트", upd_cnt])
    ws.append(["스킵", skip_cnt])
    ws.append(["오류", err_cnt])

    return wb


# =============================================================================
# 6) Celery Task: 영업가족직원조회 업로드/업데이트
# =============================================================================
@shared_task(bind=True)
def process_users_excel_task(self, task_id: str, file_path: str, batch_size: int = 500) -> dict:
    """
    ✅ '영업가족직원조회' 엑셀 업로드/업데이트 (규칙 1~3 적용)
    - 시트명 무관: REQUIRED_COLS를 모두 포함한 시트를 자동 탐색
    - division(총괄): 빈 문자열 저장(추후 보완)
    - is_staff: 전체 False / is_active: 전체 True / is_superuser: 기본 False
    - (권장 안전장치) 기존 superuser/main_admin/sub_admin은 grade/status/is_staff/is_superuser/is_active 보호
    - 진행률/상태: cache에 기록
    - 배치 처리: batch_size 단위
    - 결과 리포트 엑셀 저장 후 다운로드 가능
    """
    keys = _cache_keys(task_id)

    logger.warning("[TASK START] tid=%s file=%s", task_id, file_path)
    cache.set(keys["status"], "RUNNING", timeout=60*60)

    # ---- progress cache init
    cache.set(keys["status"], "RUNNING", timeout=60 * 60)
    cache.set(keys["percent"], 0, timeout=60 * 60)
    cache.delete(keys["error"])
    cache.delete(keys["result_path"])

    # ---- result dir
    result_dir = getattr(settings, "UPLOAD_RESULT_DIR", settings.MEDIA_ROOT / "upload_results")
    os.makedirs(result_dir, exist_ok=True)

    wb = None
    try:
        # 1) Workbook open + sheet pick
        wb = load_workbook(file_path, read_only=True, data_only=True)
        sheet_name, ws, headers = _pick_worksheet_by_required_cols(wb)

        if ws.sheet_state in ("hidden", "veryHidden"):
            raise ValueError("업로드 시트가 숨김 상태입니다. 숨김 해제 후 업로드하세요.")

        header_set = set(headers)
        missing = [c for c in REQUIRED_COLS if c not in header_set]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {', '.join(missing)} (시트: {sheet_name})")

        total = max(int(ws.max_row) - 1, 0)  # 헤더 제외

        # 2) 사원번호만 선 수집 → 기존 사용자 등급 조회(관리자 보호 판단)
        ids: List[str] = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_data = dict(zip(headers, row))
            emp_id = _normalize_emp_id(row_data.get("사원번호"))
            if emp_id:
                ids.append(emp_id)

        # existing: id -> grade
        existing_grade_map = dict(
            CustomUser.objects.filter(id__in=ids).values_list("id", "grade")
        )

        # iterator 소모 방지: workbook 재오픈
        try:
            wb.close()
        except Exception:
            pass
        wb = load_workbook(file_path, read_only=True, data_only=True)
        sheet_name, ws, headers = _pick_worksheet_by_required_cols(wb)

        results: List[List[Any]] = []
        created = updated = skipped = err_cnt = 0
        processed = 0

        buffer_rows: List[Tuple[Any, ...]] = []
        current_excel_row_num = 2  # 엑셀 실제 행번호(헤더 다음)

        def _set_percent():
            if total <= 0:
                cache.set(keys["percent"], 100, timeout=60 * 60)
                return
            p = int((processed / total) * 100)
            cache.set(keys["percent"], max(0, min(100, p)), timeout=60 * 60)

        @transaction.atomic
        def flush_chunk(rows_chunk: List[Tuple[Any, ...]], start_row_num: int):
            nonlocal created, updated, skipped, err_cnt, processed, results

            for offset, row in enumerate(rows_chunk):
                excel_row_num = start_row_num + offset
                row_data = dict(zip(headers, row))

                emp_id = _normalize_emp_id(row_data.get("사원번호"))
                name = _to_str(row_data.get("성명"))
                employed = _to_str(row_data.get("재직여부"))
                part = _to_str(row_data.get("소속부서"))
                branch = _to_str(row_data.get("영업가족명"))

                # 사원번호 없으면 스킵
                if not emp_id:
                    skipped += 1
                    results.append([excel_row_num, "", name, "", part, branch, "", "", "⚠️ 사원번호 누락(스킵)"])
                    processed += 1
                    continue

                channel = _infer_channel(part)
                grade = _infer_grade(name, employed)
                status = _infer_status(grade)
                enter = parse_date(row_data.get("입사일자(사원)"))
                quit_ = parse_date(row_data.get("퇴사일자(사원)"))

                # 기본 defaults (요청 규칙)
                defaults: Dict[str, Any] = {
                    "name": name or "",
                    "channel": channel,
                    "division": "",        # ✅ 빈값(추후 보완)
                    "part": part or "",
                    "branch": branch or "",
                    "grade": grade,
                    "status": status,
                    "enter": enter,
                    "quit": quit_,
                    "is_staff": False,     # ✅ 전체 FALSE
                    "is_active": True,     # ✅ 전체 TRUE
                    "is_superuser": False, # ✅ 기본 False
                }

                try:
                    if emp_id in existing_grade_map:
                        # ---- update
                        user = CustomUser.objects.get(id=emp_id)

                        # ---- 보호 정책: 관리자 등급은 강등/권한 필드 덮어쓰기 금지
                        if user.grade in PROTECTED_GRADES:
                            for k in ("grade", "status", "is_staff", "is_superuser", "is_active"):
                                defaults.pop(k, None)

                        # 실제 업데이트 적용
                        for k, v in defaults.items():
                            setattr(user, k, v)

                        update_fields = list(defaults.keys())
                        if update_fields:
                            user.save(update_fields=update_fields)

                        updated += 1
                        # 로그에는 "실제 최종 grade/status"를 기록(보호 정책 반영 결과 확인용)
                        results.append([
                            excel_row_num, emp_id, name, channel, part, branch,
                            getattr(user, "grade", ""), getattr(user, "status", ""), "✅ 기존 업데이트"
                        ])

                    else:
                        # ---- create (초기 비밀번호 = 사원번호)
                        CustomUser.objects.create_user(
                            id=emp_id,
                            password=emp_id,
                            **defaults,
                        )
                        existing_grade_map[emp_id] = defaults.get("grade", "basic")

                        created += 1
                        results.append([
                            excel_row_num, emp_id, name, channel, part, branch,
                            defaults.get("grade", ""), defaults.get("status", ""), "🟢 신규 등록"
                        ])

                except Exception as e:
                    err_cnt += 1
                    results.append([
                        excel_row_num, emp_id, name, channel, part, branch,
                        grade, status, f"❌ 오류: {e}"
                    ])

                processed += 1

            _set_percent()

        # 3) batch 처리
        for row in ws.iter_rows(min_row=2, values_only=True):
            buffer_rows.append(row)

            if len(buffer_rows) >= batch_size:
                flush_chunk(buffer_rows, start_row_num=current_excel_row_num)
                current_excel_row_num += len(buffer_rows)
                buffer_rows = []

        if buffer_rows:
            flush_chunk(buffer_rows, start_row_num=current_excel_row_num)

        # 4) 결과 리포트 저장
        result_wb = _make_result_wb(
            results=results,
            total=total,
            new_cnt=created,
            upd_cnt=updated,
            skip_cnt=skipped,
            err_cnt=err_cnt,
            picked_sheet=sheet_name,
        )

        result_filename = f"upload_result_{task_id}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        result_path = os.path.join(str(result_dir), result_filename)
        result_wb.save(result_path)

        cache.set(keys["percent"], 100, timeout=60 * 60)
        cache.set(keys["status"], "SUCCESS", timeout=60 * 60)
        cache.set(keys["result_path"], result_path, timeout=60 * 60)

        return {
            "status": "SUCCESS",
            "result_path": result_path,
            "sheet": sheet_name,
            "total": total,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": err_cnt,
        }

    except Exception as e:
        cache.set(keys["status"], "FAILURE", timeout=60 * 60)
        cache.set(keys["error"], str(e), timeout=60 * 60)
        raise

    finally:
        try:
            if wb:
                wb.close()
        except Exception:
            pass
