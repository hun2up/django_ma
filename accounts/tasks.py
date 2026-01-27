# django_ma/accounts/tasks.py
from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from .constants import (
    CACHE_ERROR_PREFIX,
    CACHE_PROGRESS_PREFIX,
    CACHE_RESULT_PATH_PREFIX,
    CACHE_STATUS_PREFIX,
    CACHE_TIMEOUT_SECONDS,
    EXCEL_CONTENT_TYPE,
    cache_key,
)
from .models import CustomUser

logger = logging.getLogger(__name__)

# =============================================================================
# 0) 업로드 엑셀 규격/정책 상수
# =============================================================================

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

# ✅ 관리자 보호(권장): 기존 이 등급은 엑셀로 grade 강등/권한 필드 덮어쓰기 방지
PROTECTED_GRADES = {"superuser", "head", "leader"}

PROTECTED_FIELDS = {"position", "team_a", "team_b", "team_c"}

# 결과 리포트 엑셀 시트명
RESULT_SHEET_NAME = "UploadResult"

# 진행률 표시를 위한 최소/최대 보정
PERCENT_MIN = 0
PERCENT_MAX = 100


# =============================================================================
# 1) Cache helpers (keys 단일화)
# =============================================================================

@dataclass(frozen=True)
class UploadCacheKeys:
    """업로드 진행 상태 캐시 키 번들(상수화된 prefix 규칙 기반)."""
    percent: str
    status: str
    error: str
    result_path: str


def _keys(task_id: str) -> UploadCacheKeys:
    """
    ✅ 캐시 키 규칙 단일화:
    admin.py / views.py / tasks.py 모두 동일 constants 기반.
    """
    return UploadCacheKeys(
        percent=cache_key(CACHE_PROGRESS_PREFIX, task_id),
        status=cache_key(CACHE_STATUS_PREFIX, task_id),
        error=cache_key(CACHE_ERROR_PREFIX, task_id),
        result_path=cache_key(CACHE_RESULT_PATH_PREFIX, task_id),
    )


def _cache_init(task_id: str) -> UploadCacheKeys:
    """
    업로드 시작 시 캐시 초기화(진행률/상태/오류/결과경로).
    """
    k = _keys(task_id)
    cache.set(k.status, "RUNNING", timeout=CACHE_TIMEOUT_SECONDS)
    cache.set(k.percent, 0, timeout=CACHE_TIMEOUT_SECONDS)
    cache.delete(k.error)
    cache.delete(k.result_path)
    return k


def _cache_set_percent(k: UploadCacheKeys, percent: int) -> None:
    """
    진행률 캐시 업데이트(0~100 보정).
    """
    p = max(PERCENT_MIN, min(PERCENT_MAX, int(percent)))
    cache.set(k.percent, p, timeout=CACHE_TIMEOUT_SECONDS)


def _cache_fail(k: UploadCacheKeys, err: Exception) -> None:
    """
    실패 처리(상태/에러 저장).
    """
    cache.set(k.status, "FAILURE", timeout=CACHE_TIMEOUT_SECONDS)
    cache.set(k.error, str(err), timeout=CACHE_TIMEOUT_SECONDS)


def _cache_success(k: UploadCacheKeys, result_path: str) -> None:
    """
    성공 처리(100%, SUCCESS, 결과 파일 경로 저장).
    """
    _cache_set_percent(k, 100)
    cache.set(k.status, "SUCCESS", timeout=CACHE_TIMEOUT_SECONDS)
    cache.set(k.result_path, result_path, timeout=CACHE_TIMEOUT_SECONDS)


# =============================================================================
# 2) Result dir helper
# =============================================================================

def _get_result_dir() -> Path:
    """
    결과 리포트 저장 폴더 결정:
    - settings.UPLOAD_RESULT_DIR 있으면 우선
    - 없으면 MEDIA_ROOT/upload_results
    """
    media_root = Path(getattr(settings, "MEDIA_ROOT", "media"))
    default_dir = media_root / "upload_results"
    result_dir = Path(getattr(settings, "UPLOAD_RESULT_DIR", default_dir))
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir



# =============================================================================
# 3) 공용 유틸 (문자/사원번호/날짜 파싱)
# =============================================================================

def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()


def _is_nan(v) -> bool:
    return isinstance(v, float) and math.isnan(v)


def _normalize_emp_id(v) -> str:
    """
    엑셀 '사원번호'가 float(2533454.0)로 들어오는 케이스 정규화.
    - None/NaN → ""
    - int/정수형 float → 정수 문자열
    - "2533454.0" → "2533454"
    """
    if v is None or _is_nan(v):
        return ""

    # 숫자 케이스 선처리
    try:
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float) and float(v).is_integer():
            return str(int(v))
    except Exception:
        pass

    s = _to_str(v)
    if not s:
        return ""

    if s.endswith(".0"):
        s = s[:-2]

    return s


def parse_date(value) -> Optional[date]:
    """
    엑셀 날짜가 datetime/date/문자열 혼합으로 올 수 있어 안전 변환.
    """
    if value is None or _is_nan(value):
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = _to_str(value)
    if not s:
        return None

    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


# =============================================================================
# 4) 요청 규칙(부문/권한/상태) 계산
# =============================================================================

def _infer_channel(part_text: str) -> str:
    """
    규칙 1. 부문 설정
      - 소속부서에 'GA' 포함 -> 'MA부문'
      - 소속부서에 'MA' 포함 -> 'MA부문'
      - 소속부서에 'CA' 포함 -> 'CA부문'
      - 소속부서에 'PA' 포함 -> 'PA부문'
      - 그 외 -> '전략부문'
    """
    t = _to_str(part_text).upper()
    # ✅ GA/MA 우선 (요청하신 정책)
    if "GA" in t or "MA" in t:
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
    ✅ 우선순위: inactive 최상
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
# 5) 엑셀 시트 선택 로직 (시트명 무관)
#    - "필수 컬럼이 모두 존재하는 첫 시트"를 자동 선택
# =============================================================================

def _read_header(ws) -> list[str]:
    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not header:
        return []
    return [_to_str(v) for v in header]


def _pick_worksheet_by_required_cols(wb):
    """
    업로드 엑셀에서 REQUIRED_COLS를 모두 포함한 첫 번째 '표시(visible)' 시트를 선택한다.
    - 숨김 시트는 제외
    - 못 찾으면 가독성 좋은 에러 메시지로 예외 발생
    """
    for name in wb.sheetnames:
        ws = wb[name]
        if ws.sheet_state in ("hidden", "veryHidden"):
            continue

        headers = _read_header(ws)
        header_set = set(headers)
        if all(c in header_set for c in REQUIRED_COLS):
            return name, ws, headers

    # 디버깅을 돕기 위한 정보 첨부
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
# 6) 결과 리포트 엑셀 생성
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
    """
    업로드 처리 결과를 사람이 확인하기 쉬운 형태로 엑셀 리포트로 생성.
    - Result 컬럼에 아이콘(🟢/✅/⚠️/❌) 포함 → 셀 색상 표시
    """
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


def _save_result_workbook(task_id: str, result_wb: Workbook) -> str:
    """
    결과 리포트 엑셀 파일을 디스크에 저장하고 저장 경로를 반환.
    """
    result_dir = _get_result_dir()
    filename = f"upload_result_{task_id}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    path = result_dir / filename
    result_wb.save(str(path))
    return str(path)



# =============================================================================
# 7) Celery Task: 영업가족직원조회 업로드/업데이트
# =============================================================================

@shared_task(bind=True)
def process_users_excel_task(self, task_id: str, file_path: str, batch_size: int = 500) -> dict:
    """
    ✅ '영업가족직원조회' 엑셀 업로드/업데이트 (규칙 1~3 적용)

    주요 동작:
    - 시트명 무관: REQUIRED_COLS를 모두 포함한 시트를 자동 탐색
    - division(총괄): 빈 문자열 저장
    - is_staff: 전체 False / is_superuser: 기본 False
    - is_active: 기존 코드 정책 유지 (grade != inactive)
    - 관리자 보호(권장): 기존 superuser/head/leader은 grade/status/is_staff/is_superuser/is_active 덮어쓰기 금지
    - 진행률/상태/오류/결과경로: cache에 기록 (constants 기반 key 단일화)
    - 배치 처리: batch_size 단위 transaction
    - 결과 리포트 엑셀 저장 후 다운로드 가능
    """
    k = _cache_init(task_id)
    logger.warning("[TASK START] tid=%s file=%s batch=%s", task_id, file_path, batch_size)

    wb = None
    try:
        # ---------------------------------------------------------------------
        # 1) Workbook open + 업로드 시트 자동 선택
        # ---------------------------------------------------------------------
        wb = load_workbook(file_path, read_only=True, data_only=True)
        sheet_name, ws, headers = _pick_worksheet_by_required_cols(wb)

        if ws.sheet_state in ("hidden", "veryHidden"):
            raise ValueError("업로드 시트가 숨김 상태입니다. 숨김 해제 후 업로드하세요.")

        header_set = set(headers)
        missing = [c for c in REQUIRED_COLS if c not in header_set]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {', '.join(missing)} (시트: {sheet_name})")

        total = max(int(ws.max_row) - 1, 0)  # 헤더 제외

        # ---------------------------------------------------------------------
        # 2) 사원번호 선 수집 → 기존 사용자 등급 조회(관리자 보호 판단)
        #    (read_only iterator 1회 소모 방지를 위해: 선 수집 후 workbook 재오픈)
        # ---------------------------------------------------------------------
        ids: List[str] = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_data = dict(zip(headers, row))
            emp_id = _normalize_emp_id(row_data.get("사원번호"))
            if emp_id:
                ids.append(emp_id)

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

        # ---------------------------------------------------------------------
        # 3) 배치 처리 준비
        # ---------------------------------------------------------------------
        results: List[List[Any]] = []
        created = updated = skipped = err_cnt = 0
        processed = 0

        buffer_rows: List[Tuple[Any, ...]] = []
        current_excel_row_num = 2  # 엑셀 실제 행번호(헤더 다음)

        def set_percent_from_processed() -> None:
            if total <= 0:
                _cache_set_percent(k, 100)
                return
            p = int((processed / total) * 100)
            _cache_set_percent(k, p)

        @transaction.atomic
        def flush_chunk(rows_chunk: List[Tuple[Any, ...]], start_row_num: int) -> None:
            """
            배치 단위로 CustomUser 업서트 수행.
            - transaction.atomic으로 chunk 단위 원자성 확보
            """
            nonlocal created, updated, skipped, err_cnt, processed, results, existing_grade_map

            for offset, row in enumerate(rows_chunk):
                excel_row_num = start_row_num + offset
                row_data = dict(zip(headers, row))

                emp_id = _normalize_emp_id(row_data.get("사원번호"))
                name = _to_str(row_data.get("성명"))
                employed = _to_str(row_data.get("재직여부"))
                part = _to_str(row_data.get("소속부서"))
                branch = _to_str(row_data.get("영업가족명"))

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

                # ✅ 기존 코드의 defaults 정책 유지
                defaults: Dict[str, Any] = {
                    "name": name or "",
                    "channel": channel,
                    "division": "",          # 빈값 유지
                    "part": part or "",
                    "branch": branch or "",
                    "grade": grade,
                    "status": status,
                    "enter": enter,
                    "quit": quit_,
                    "is_staff": False,       # 전체 False
                    "is_active": (grade != "inactive"),
                    "is_superuser": False,   # 기본 False
                }

                try:
                    # ---------------------------------------------------------
                    # Update path (퇴사일 정책 반영)
                    # ---------------------------------------------------------
                    if emp_id in existing_grade_map:
                        user = CustomUser.objects.get(id=emp_id)

                        # ✅ 보호등급(superuser/head/leader) 퇴사일 정책
                        is_protected = user.grade in PROTECTED_GRADES

                        # "퇴사일이 새로 생긴 경우" 정의: DB에 quit이 없었는데, 이번 엑셀엔 quit이 들어온 경우
                        quit_newly_added = (user.quit is None and quit_ is not None)

                        # 1) 보호등급 + 퇴사일 신규 생성 아님 → 엑셀로 변경 금지 (grade가 뭐로 와도 유지)
                        if is_protected and not quit_newly_added:
                            skipped += 1
                            results.append([
                                excel_row_num,
                                emp_id,
                                name,
                                channel,
                                part,
                                branch,
                                getattr(user, "grade", ""),
                                getattr(user, "status", ""),
                                "⚠️ 보호등급(superuser/head/leader) - 퇴사일 신규 없음(변경 차단)",
                            ])
                            processed += 1
                            continue

                        # 2) 보호등급 + 퇴사일 신규 생성 → 기존 정책에 따라 resign/inactive로 강제 전환
                        #    (엑셀의 grade 값이 basic/resign 뭐로 와도, 최종 결정은 기존 정책)
                        if is_protected and quit_newly_added:
                            forced_grade = "inactive" if ((not name) or ("*" in name)) else "resign"
                            forced_status = _infer_status(forced_grade)

                            defaults["grade"] = forced_grade
                            defaults["status"] = forced_status
                            defaults["quit"] = quit_
                            defaults["is_active"] = (forced_grade != "inactive")
                            defaults["is_staff"] = False
                            defaults["is_superuser"] = False

                        # (참고) 이제 PROTECTED_GRADES는 superuser/head/leader만 포함이므로
                        # 예전처럼 pop()으로 보호 필드를 제거하는 방식은 "퇴사일 신규 생성" 케이스를 막을 수 있어
                        # 여기서는 pop()을 사용하지 않고 위 조건으로 흐름을 제어한다.

                        # 반영
                        # ---------------------------------------------------------
                        # Update path (보호 필드 정책 반영)
                        # ---------------------------------------------------------
                        user = CustomUser.objects.get(id=emp_id)

                        is_protected_grade = user.grade in PROTECTED_GRADES
                        quit_newly_added = (user.quit is None and quit_ is not None)

                        update_fields: List[str] = []

                        for key, value in defaults.items():

                            # 1) 보호 필드 처리
                            if key in PROTECTED_FIELDS:
                                if value:
                                    # 값이 있으면 명시적 변경 허용
                                    setattr(user, key, value)
                                    update_fields.append(key)
                                else:
                                    # 빈 값인 경우
                                    if quit_newly_added:
                                        # 재직 → 퇴사 전환 시에만 초기화 허용
                                        setattr(user, key, "")
                                        update_fields.append(key)
                                    # else: 기존 값 유지 (아무 것도 안 함)
                                continue

                            # 2) 일반 필드 처리
                            if value != "":
                                setattr(user, key, value)
                                update_fields.append(key)

                        # 보호 등급 + 퇴사일 신규 없는 경우는 위에서 continue 처리됨
                        if update_fields:
                            user.save(update_fields=update_fields)

                        existing_grade_map[emp_id] = user.grade


                        existing_grade_map[emp_id] = user.grade

                        updated += 1
                        results.append([
                            excel_row_num,
                            emp_id,
                            name,
                            channel,
                            part,
                            branch,
                            getattr(user, "grade", ""),
                            getattr(user, "status", ""),
                            "✅ 기존 업데이트",
                        ])

                    # ---------------------------------------------------------
                    # Create path
                    # ---------------------------------------------------------
                    else:
                        CustomUser.objects.create_user(
                            id=emp_id,
                            password=emp_id,  # 초기 비밀번호 = 사원번호
                            **defaults,
                        )
                        existing_grade_map[emp_id] = defaults.get("grade", "basic")

                        created += 1
                        results.append([
                            excel_row_num,
                            emp_id,
                            name,
                            channel,
                            part,
                            branch,
                            defaults.get("grade", ""),
                            defaults.get("status", ""),
                            "🟢 신규 등록",
                        ])

                except Exception as e:
                    err_cnt += 1
                    results.append([excel_row_num, emp_id, name, channel, part, branch, grade, status, f"❌ 오류: {e}"])

                processed += 1

            set_percent_from_processed()



        # ---------------------------------------------------------------------
        # 4) batch loop
        # ---------------------------------------------------------------------
        for row in ws.iter_rows(min_row=2, values_only=True):
            buffer_rows.append(row)

            if len(buffer_rows) >= batch_size:
                flush_chunk(buffer_rows, start_row_num=current_excel_row_num)
                current_excel_row_num += len(buffer_rows)
                buffer_rows = []

        if buffer_rows:
            flush_chunk(buffer_rows, start_row_num=current_excel_row_num)

        # ---------------------------------------------------------------------
        # 5) 결과 리포트 생성 + 저장
        # ---------------------------------------------------------------------
        result_wb = _make_result_wb(
            results=results,
            total=total,
            new_cnt=created,
            upd_cnt=updated,
            skip_cnt=skipped,
            err_cnt=err_cnt,
            picked_sheet=sheet_name,
        )

        result_path = _save_result_workbook(task_id, result_wb)

        # ---------------------------------------------------------------------
        # 6) cache finalize (SUCCESS)
        # ---------------------------------------------------------------------
        _cache_success(k, result_path)

        logger.warning(
            "[TASK DONE] tid=%s status=SUCCESS sheet=%s total=%s created=%s updated=%s skipped=%s errors=%s",
            task_id, sheet_name, total, created, updated, skipped, err_cnt
        )

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
        # ---------------------------------------------------------------------
        # failure (cache 기록 + raise)
        # ---------------------------------------------------------------------
        logger.exception("[TASK FAIL] tid=%s file=%s", task_id, file_path)
        _cache_fail(k, e)
        raise

    finally:
        # ---------------------------------------------------------------------
        # workbook close
        # ---------------------------------------------------------------------
        try:
            if wb:
                wb.close()
        except Exception:
            pass
