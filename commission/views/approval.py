# django_ma/commission/views/approval.py
from __future__ import annotations

from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from commission.upload_handlers import (
    _handle_upload_commission_approval,
    _handle_upload_efficiency_pay_excess,
)
from commission.upload_utils import _read_excel_raw_matrix

from ..models import ApprovalExcelUploadLog, ApprovalPending, EfficiencyPayExcess
from .utils_fail_excel import store_fail_rows_as_excel
from .utils_json import _json_error, _json_ok


def _pad2(n: int) -> str:
    return f"{n:02d}"


def _validate_ym(year: str, month: str) -> str:
    if not (year or "").isdigit():
        raise ValueError("연도를 선택해주세요.")
    if not (month or "").isdigit():
        raise ValueError("월도를 선택해주세요.")

    y = int(year)
    m = int(month)
    if m < 1 or m > 12:
        raise ValueError("월도는 1~12 범위여야 합니다.")

    return f"{y}-{_pad2(m)}"


def _common_upload(*, request, ym: str, part: str, kind: str, file_path: str, original_name: str) -> tuple[int, int, dict]:
    """
    approval/efficiency 공통 업로드 SSOT

    Steps:
      1) raw matrix로 row_count 산정
      2) 기존 데이터(ym + part scope) 삭제
      3) handler 실행
      4) ApprovalExcelUploadLog update_or_create
    """
    df_raw = _read_excel_raw_matrix(file_path, original_name=original_name, skiprows=0, header_none=True)
    row_count = int(len(df_raw.index)) if df_raw is not None else 0

    if kind == "approval":
        del_qs = ApprovalPending.objects.filter(ym=ym)
        if part:
            del_qs = del_qs.filter(user__part=part)
        del_qs.delete()

        result = _handle_upload_commission_approval(
            file_path=file_path,
            original_name=original_name,
            ym=ym,
            part=part,
        )
        inserted = int(result.get("inserted_or_updated") or 0)

    elif kind == "efficiency":
        del_qs = EfficiencyPayExcess.objects.filter(ym=ym)
        if part:
            del_qs = del_qs.filter(user__part=part)
        del_qs.delete()

        result = _handle_upload_efficiency_pay_excess(
            file_path=file_path,
            original_name=original_name,
            ym=ym,
            part=part,
        )
        inserted = int(result.get("inserted_or_updated") or 0)

    else:
        raise ValueError("구분(kind)을 선택해주세요. (efficiency/approval)")

    ApprovalExcelUploadLog.objects.update_or_create(
        ym=ym,
        part=part,
        kind=kind,
        defaults={
            "uploaded_by": request.user,
            "row_count": row_count,
            "file_name": (original_name or "")[:255],
        },
    )

    return row_count, inserted, result


@csrf_exempt
@require_POST
@grade_required("superuser")
def approval_upload_excel(request):
    year = (request.POST.get("year") or request.GET.get("year") or "").strip()
    month = (request.POST.get("month") or request.GET.get("month") or "").strip()
    part = (request.POST.get("part") or request.GET.get("part") or "").strip()
    kind = (request.POST.get("kind") or request.GET.get("kind") or "").strip()
    excel_file = request.FILES.get("excel_file")

    try:
        ym = _validate_ym(year, month)
    except ValueError as ve:
        return _json_error(str(ve), status=400)

    if kind not in ("efficiency", "approval"):
        return _json_error("구분(kind)을 선택해주세요. (efficiency/approval)", status=400)
    if not excel_file:
        return _json_error("엑셀 파일이 전달되지 않았습니다.", status=400)

    fs = FileSystemStorage()
    saved_name = fs.save(excel_file.name, excel_file)
    file_path = fs.path(saved_name)

    try:
        with transaction.atomic():
            row_count, inserted, result = _common_upload(
                request=request,
                ym=ym,
                part=part,
                kind=kind,
                file_path=file_path,
                original_name=excel_file.name,
            )

        missing_sample = result.get("missing_sample", []) or []
        fail_token = ""
        if missing_sample:
            rows = [{"user_id": uid, "reason": "사용자 미존재 또는 part 스코프 제외"} for uid in missing_sample]
            fail_token = store_fail_rows_as_excel(
                rows=rows,
                filename=f"upload_fail_{ym}_{part or 'ALL'}_{kind}.xlsx",
            )

        return _json_ok(
            "✅ 업로드가 완료되었습니다.",
            ym=ym,
            part=part,
            kind=kind,
            row_count=row_count,
            file_name=excel_file.name,
            inserted=inserted,
            missing_users=int(result.get("missing_users") or 0),
            missing_sample=missing_sample,
            fail_token=fail_token,
            fail_download_url=(f"/commission/download/upload-fail/?token={fail_token}" if fail_token else ""),
        )

    except ValueError as ve:
        return _json_error(str(ve), status=400)

    except Exception as e:
        return _json_error(f"⚠️ 업로드 실패: {e}", status=500)

    finally:
        try:
            fs.delete(saved_name)
        except Exception:
            pass
