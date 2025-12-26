# django_ma/accounts/tasks.py
from __future__ import annotations

import os
from io import BytesIO
from datetime import datetime, date

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill

from .models import CustomUser


EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
UPLOAD_SHEET_NAME = "업로드"

GRADE_MAP = {
    "superuser": "superuser",
    "main_admin": "main_admin",
    "sub_admin": "sub_admin",
    "basic": "basic",
    "inactive": "inactive",
}

def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()

def parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = _to_str(value)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def parse_bool(value, default: bool = True) -> bool:
    s = _to_str(value).lower()
    if s in {"true", "1", "yes", "y", "t"}:
        return True
    if s in {"false", "0", "no", "n", "f"}:
        return False
    return default

def _cache_keys(task_id: str) -> dict:
    return {
        "percent": f"upload_progress:{task_id}",
        "status": f"upload_status:{task_id}",
        "error": f"upload_error:{task_id}",
        "result_path": f"upload_result_path:{task_id}",
    }

def _make_result_wb(results: list[list], total: int, new_cnt: int, upd_cnt: int, err_cnt: int) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "UploadResult"

    ws.append(["Row", "ID", "Name", "Result"])

    fill_new = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_update = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    fill_error = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row in results:
        ws.append(row)
        r = ws.max_row
        t = _to_str(row[-1])
        if "신규" in t:
            ws[f"D{r}"].fill = fill_new
        elif "업데이트" in t:
            ws[f"D{r}"].fill = fill_update
        elif "오류" in t or "누락" in t:
            ws[f"D{r}"].fill = fill_error

    ws.append([])
    ws.append(["총 데이터", total])
    ws.append(["신규 추가", new_cnt])
    ws.append(["업데이트", upd_cnt])
    ws.append(["오류", err_cnt])
    return wb

@shared_task(bind=True)
def process_users_excel_task(self, task_id: str, file_path: str, batch_size: int = 500) -> dict:
    """
    엑셀 업로드를 백그라운드에서 처리:
    - 500행 단위 청크 처리
    - cache로 진행률/상태 업데이트
    - 결과 리포트 엑셀 저장 후 다운로드 가능
    """
    keys = _cache_keys(task_id)

    cache.set(keys["status"], "RUNNING", timeout=60 * 60)
    cache.set(keys["percent"], 0, timeout=60 * 60)
    cache.delete(keys["error"])
    cache.delete(keys["result_path"])

    # 저장 폴더 준비
    result_dir = getattr(settings, "UPLOAD_RESULT_DIR", settings.MEDIA_ROOT / "upload_results")
    temp_dir = getattr(settings, "UPLOAD_TEMP_DIR", settings.MEDIA_ROOT / "upload_temp")
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        wb = load_workbook(file_path, read_only=True, data_only=True)
        if UPLOAD_SHEET_NAME not in wb.sheetnames:
            raise ValueError(f"'{UPLOAD_SHEET_NAME}' 시트를 찾을 수 없습니다.")
        ws = wb[UPLOAD_SHEET_NAME]
        if ws.sheet_state in ["hidden", "veryHidden"]:
            raise ValueError("'업로드' 시트가 숨김 상태입니다.")

        headers = [_to_str(c.value) for c in ws[1]]
        total = max(ws.max_row - 1, 0)  # 헤더 제외

        # 기존 사용자 미리 조회(속도↑)
        # - 엑셀을 1번 훑어 ids만 수집 (3300이면 메모리 부담 거의 없음)
        ids = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_data = dict(zip(headers, row))
            uid = _to_str(row_data.get("사번"))
            if uid:
                ids.append(uid)

        existing_ids = set(
            CustomUser.objects.filter(id__in=ids).values_list("id", flat=True)
        )

        # 다시 시트 iterator를 만들기 위해 workbook 재오픈(읽기전용은 iterator 소모됨)
        wb.close()
        wb = load_workbook(file_path, read_only=True, data_only=True)
        ws = wb[UPLOAD_SHEET_NAME]
        headers = [_to_str(c.value) for c in ws[1]]

        results: list[list] = []
        success_new = success_update = error_count = 0

        buffer_rows = []
        processed = 0

        def flush_chunk(buffer_rows_local: list[tuple], start_excel_row: int):
            nonlocal success_new, success_update, error_count, processed, results

            # 청크 내에서 처리(한 행씩 저장하되, 기존 조회는 set으로 빠르게 판단)
            for offset, row in enumerate(buffer_rows_local):
                excel_row_num = start_excel_row + offset
                row_data = dict(zip(headers, row))

                user_id = _to_str(row_data.get("사번"))
                name = _to_str(row_data.get("성명"))

                if not user_id or not name:
                    results.append([excel_row_num, user_id, name, "❌ ID 또는 이름 누락"])
                    error_count += 1
                    processed += 1
                    continue

                grade_raw = _to_str(row_data.get("등급")).lower()
                grade_val = GRADE_MAP.get(grade_raw, "basic")

                status_val = _to_str(row_data.get("상태")) or "재직"
                is_superuser = grade_val == "superuser"
                is_staff = grade_val in {"superuser", "main_admin", "sub_admin"}

                is_active = parse_bool(
                    row_data.get("IS_ACTIVE") if row_data.get("IS_ACTIVE") is not None else row_data.get("is_active"),
                    default=True,
                )

                defaults = dict(
                    name=name,
                    channel=_to_str(row_data.get("채널")),
                    part=_to_str(row_data.get("부서")),
                    branch=_to_str(row_data.get("지점")),
                    grade=grade_val,
                    status=status_val,
                    regist=_to_str(row_data.get("손생등록여부")),
                    birth=parse_date(row_data.get("생년월일")),
                    enter=parse_date(row_data.get("입사일")),
                    quit=parse_date(row_data.get("퇴사일")),
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )

                try:
                    if user_id in existing_ids:
                        # update
                        user = CustomUser.objects.get(id=user_id)
                        for k, v in defaults.items():
                            setattr(user, k, v)
                        user.save()
                        success_update += 1
                        results.append([excel_row_num, user_id, name, "✅ 기존 업데이트"])
                    else:
                        CustomUser.objects.create_user(
                            id=user_id,
                            password=_to_str(row_data.get("비밀번호")) or user_id,
                            **defaults,
                        )
                        existing_ids.add(user_id)
                        success_new += 1
                        results.append([excel_row_num, user_id, name, "🟢 신규 등록"])
                except Exception as e:
                    error_count += 1
                    results.append([excel_row_num, user_id, name, f"❌ 오류: {e}"])

                processed += 1

            # 진행률 업데이트
            if total > 0:
                percent = int((processed / total) * 100)
                cache.set(keys["percent"], percent, timeout=60 * 60)

        # 실제 처리 루프 (500행 단위)
        start_row_num = 2
        current_row_num = 2
        for row in ws.iter_rows(min_row=2, values_only=True):
            buffer_rows.append(row)
            if len(buffer_rows) >= batch_size:
                flush_chunk(buffer_rows, start_excel_row=current_row_num)
                current_row_num += len(buffer_rows)
                buffer_rows = []

        if buffer_rows:
            flush_chunk(buffer_rows, start_excel_row=current_row_num)

        # 결과 리포트 생성/저장
        result_wb = _make_result_wb(results, total, success_new, success_update, error_count)
        result_filename = f"upload_result_{task_id}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        result_path = os.path.join(str(result_dir), result_filename)
        result_wb.save(result_path)

        cache.set(keys["percent"], 100, timeout=60 * 60)
        cache.set(keys["status"], "SUCCESS", timeout=60 * 60)
        cache.set(keys["result_path"], result_path, timeout=60 * 60)

        return {"status": "SUCCESS", "result_path": result_path}

    except Exception as e:
        cache.set(keys["status"], "FAILURE", timeout=60 * 60)
        cache.set(keys["error"], str(e), timeout=60 * 60)
        raise
    finally:
        try:
            wb.close()
        except Exception:
            pass
