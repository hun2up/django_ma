# django_ma/commission/views/downloads.py
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from ..models import ApprovalPending, EfficiencyPayExcess
from .utils_json import _json_error, _set_attachment_filename


@require_GET
def download_upload_fail_excel(request):
    """
    업로드 실패 목록 엑셀 다운로드 (token 기반)
      예) /commission/download/upload-fail/?token=xxxx
    """
    token = (request.GET.get("token") or "").strip()
    if not token:
        return _json_error("token이 필요합니다.", status=400)

    key = f"commission:upload_fail:{token}"
    payload = cache.get(key)
    if not payload:
        return _json_error("만료되었거나 존재하지 않는 token입니다.", status=404)

    content = payload.get("content")
    filename = payload.get("filename") or f"upload_fail_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    if not content:
        return _json_error("파일 데이터가 비어있습니다.", status=404)

    resp = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    _set_attachment_filename(resp, filename)
    return resp


@require_GET
def download_approval_pending_excel(request):
    """
    수수료 미결현황 엑셀 다운로드
    - GET 파라미터: ym(YYYY-MM) optional
    - ym 없으면 최신 ym 기준
    """
    ym = (request.GET.get("ym") or "").strip()

    qs = ApprovalPending.objects.all().select_related("user")
    if ym:
        qs = qs.filter(ym=ym)
    else:
        latest = qs.order_by("-ym").values_list("ym", flat=True).first()
        if not latest:
            return _json_error("다운로드할 데이터가 없습니다.", status=404)
        ym = latest
        qs = qs.filter(ym=ym)

    rows = [
        {
            "ym": r.ym,
            "user_id": str(r.user_id),
            "emp_name": r.emp_name,
            "actual_pay": int(r.actual_pay or 0),
            "approval_flag": r.approval_flag,
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        }
        for r in qs.order_by("user_id")
    ]
    if not rows:
        return _json_error("해당 조건의 데이터가 없습니다.", status=404)

    df = pd.DataFrame(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="approval_pending")

    resp = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    _set_attachment_filename(resp, f"approval_pending_{ym}.xlsx")
    return resp


@require_GET
def download_efficiency_excess_excel(request):
    """
    지점효율 지급 초과현황 엑셀 다운로드
    - GET 파라미터: ym(YYYY-MM) optional
    - ym 없으면 최신 ym 기준
    """
    ym = (request.GET.get("ym") or "").strip()

    qs = EfficiencyPayExcess.objects.all().select_related("user")
    if ym:
        qs = qs.filter(ym=ym)
    else:
        latest = qs.order_by("-ym").values_list("ym", flat=True).first()
        if not latest:
            return _json_error("다운로드할 데이터가 없습니다.", status=404)
        ym = latest
        qs = qs.filter(ym=ym)

    rows = [
        {
            "ym": r.ym,
            "user_id": str(r.user_id),
            "pay_amount_sum": int(r.pay_amount_sum or 0),
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        }
        for r in qs.order_by("user_id")
    ]
    if not rows:
        return _json_error("해당 조건의 데이터가 없습니다.", status=404)

    df = pd.DataFrame(rows)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="efficiency_excess")

    resp = HttpResponse(
        out.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    _set_attachment_filename(resp, f"efficiency_excess_{ym}.xlsx")
    return resp
