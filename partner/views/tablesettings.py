# partner/views/tablesettings.py
# ------------------------------------------------------------
# ✅ TableSetting (테이블관리) API
# ------------------------------------------------------------

import traceback

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from partner.models import TableSetting

from .responses import json_err, json_ok, parse_json_body


@require_GET
@login_required
@grade_required("superuser", "head", "leader")
def ajax_table_fetch(request):
    branch = (request.GET.get("branch") or "").strip()
    user = request.user

    if not branch:
        return json_err("지점(branch) 정보가 없습니다.", status=400)
    if user.grade != "superuser" and branch != user.branch:
        return json_err("다른 지점 테이블에는 접근할 수 없습니다.", status=403)

    try:
        rows = (
            TableSetting.objects.filter(branch=branch)
            .order_by("order")
            .values("order", "branch", "table_name", "rate", "created_at", "updated_at")
        )
        data = [
            {
                "order": r["order"],
                "branch": r["branch"],
                "table": r["table_name"],
                "rate": r["rate"],
                "created_at": r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "-",
                "updated_at": r["updated_at"].strftime("%Y-%m-%d") if r["updated_at"] else "-",
            }
            for r in rows
        ]
        return json_ok({"rows": data})
    except Exception as e:
        traceback.print_exc()
        return json_err(f"조회 중 오류 발생: {str(e)}", status=500)


@require_POST
@login_required
@grade_required("superuser", "head")
def ajax_table_save(request):
    try:
        data = parse_json_body(request)
        branch = (data.get("branch") or "").strip()
        rows = data.get("rows", [])

        if not branch or not isinstance(rows, list):
            return json_err("요청 데이터가 잘못되었습니다.", status=400)

        with transaction.atomic():
            TableSetting.objects.filter(branch=branch).delete()

            objs = []
            for r in rows:
                order = int(r.get("order") or 0)
                table_name = (r.get("table") or "").strip()
                rate = (r.get("rate") or "").strip()
                if not table_name and not rate:
                    continue
                objs.append(TableSetting(branch=branch, table_name=table_name, rate=rate, order=order))

            TableSetting.objects.bulk_create(objs)

        return json_ok({"saved_count": len(objs)})
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)
