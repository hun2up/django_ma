# partner/views/ratetable.py
# ------------------------------------------------------------
# ✅ RateTable (요율현황) API
# - userlist/json
# - excel download
# - excel upload
# - user detail
# - template excel
# ------------------------------------------------------------

import io
import traceback
from datetime import datetime

import pandas as pd
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.db import transaction

from accounts.models import CustomUser
from partner.models import RateTable, SubAdminTemp

from .responses import json_err, json_ok
from .utils import find_table_rate


@require_GET
def ajax_rate_userlist(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"data": []})

    users = CustomUser.objects.filter(branch=branch, is_active=True).values("id", "name", "branch").order_by("name")
    user_ids = [u["id"] for u in users]

    team_map = {
        t.user_id: {"team_a": t.team_a, "team_b": t.team_b, "team_c": t.team_c}
        for t in SubAdminTemp.objects.filter(user_id__in=user_ids)
    }
    rate_map = {
        r.user_id: {"non_life_table": r.non_life_table or "", "life_table": r.life_table or ""}
        for r in RateTable.objects.filter(user_id__in=user_ids)
    }

    data = []
    for u in users:
        team_info = team_map.get(u["id"], {})
        rate_info = rate_map.get(u["id"], {})
        data.append(
            {
                "id": u["id"],
                "name": u["name"],
                "branch": u["branch"],
                "team_a": team_info.get("team_a", ""),
                "team_b": team_info.get("team_b", ""),
                "team_c": team_info.get("team_c", ""),
                "non_life_table": rate_info.get("non_life_table", ""),
                "life_table": rate_info.get("life_table", ""),
            }
        )
    return JsonResponse({"data": data})


def ajax_rate_userlist_excel(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"error": "지점을 선택해주세요."}, status=400)

    user = request.user
    if user.grade != "superuser" and branch != user.branch:
        return JsonResponse({"error": "다른 지점 데이터에는 접근할 수 없습니다."}, status=403)

    users = list(
        CustomUser.objects.filter(branch=branch, is_active=True).values("id", "name", "branch").order_by("name")
    )
    user_ids = [u["id"] for u in users]

    team_map = {
        t.user_id: {"team_a": t.team_a, "team_b": t.team_b, "team_c": t.team_c}
        for t in SubAdminTemp.objects.filter(user_id__in=user_ids)
    }
    rate_map = {
        r.user_id: {"non_life_table": r.non_life_table or "", "life_table": r.life_table or ""}
        for r in RateTable.objects.filter(user_id__in=user_ids)
    }

    data = []
    for u in users:
        team_info = team_map.get(u["id"], {})
        rate_info = rate_map.get(u["id"], {})
        data.append(
            {
                "지점": u["branch"],
                "팀A": team_info.get("team_a", ""),
                "팀B": team_info.get("team_b", ""),
                "팀C": team_info.get("team_c", ""),
                "성명": u["name"],
                "사번": u["id"],
                "손보테이블": rate_info.get("non_life_table", ""),
                "생보테이블": rate_info.get("life_table", ""),
            }
        )

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="요율현황")

    filename = f"요율현황_{branch}_{datetime.now():%Y%m%d}.xlsx"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_POST
@transaction.atomic
def ajax_rate_userlist_upload(request):
    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return json_err("엑셀 파일이 없습니다.", status=400)

    try:
        file_path = default_storage.save(f"tmp/{excel_file.name}", excel_file)
        file_path_full = default_storage.path(file_path)

        df = pd.read_excel(file_path_full, sheet_name="업로드").fillna("")
        required_cols = ["사번", "손보테이블", "생보테이블"]
        for col in required_cols:
            if col not in df.columns:
                default_storage.delete(file_path)
                return json_err(f"'{col}' 컬럼이 없습니다.", status=400)

        updated_count, skipped_count = 0, 0
        for _, row in df.iterrows():
            user_id = str(row["사번"]).strip()
            if not user_id:
                skipped_count += 1
                continue

            u = CustomUser.objects.filter(id=user_id).first()
            if not u:
                skipped_count += 1
                continue

            RateTable.objects.update_or_create(
                user=u,
                defaults={"non_life_table": row["손보테이블"], "life_table": row["생보테이블"]},
            )
            updated_count += 1

        default_storage.delete(file_path)
        return json_ok({"message": f"업로드 완료 ({updated_count}건 업데이트 / {skipped_count}건 스킵됨)"})
    except Exception as e:
        traceback.print_exc()
        return json_err(f"업로드 중 오류: {str(e)}", status=500)


@require_GET
def ajax_rate_user_detail(request):
    user_id = (request.GET.get("user_id") or "").strip()
    if not user_id:
        return json_err("user_id가 없습니다.", status=400)

    try:
        target = CustomUser.objects.get(id=user_id)

        rate_info = RateTable.objects.filter(user=target).first()
        non_life_table = rate_info.non_life_table if rate_info else ""
        life_table = rate_info.life_table if rate_info else ""

        non_life_rate = find_table_rate(target.branch, non_life_table)
        life_rate = find_table_rate(target.branch, life_table)

        return json_ok(
            {
                "data": {
                    "target_name": target.name,
                    "target_id": target.id,
                    "non_life_table": non_life_table,
                    "life_table": life_table,
                    "non_life_rate": non_life_rate,
                    "life_rate": life_rate,
                    "branch": target.branch or "",
                }
            }
        )
    except CustomUser.DoesNotExist:
        return json_err("대상자를 찾을 수 없습니다.", status=404)
    except Exception as e:
        traceback.print_exc()
        return json_err(str(e), status=500)


@require_GET
def ajax_rate_userlist_template_excel(request):
    try:
        branch = (request.GET.get("branch") or "").strip()
        df = pd.DataFrame(columns=["사번", "손보테이블", "생보테이블"])

        guide = pd.DataFrame(
            [
                ["업로드 시트명은 반드시 '업로드' 이어야 합니다.", "", ""],
                ["컬럼명은 정확히: 사번 / 손보테이블 / 생보테이블", "", ""],
                ["사번은 CustomUser.id와 매칭됩니다.", "", ""],
            ],
            columns=["안내", " ", "  "],
        )

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="업로드")
            guide.to_excel(writer, index=False, sheet_name="안내")
            ws = writer.book["업로드"]
            ws.column_dimensions["A"].width = 14
            ws.column_dimensions["B"].width = 20
            ws.column_dimensions["C"].width = 20

        filename = f"요율현황_업로드양식_{branch+'_' if branch else ''}{datetime.now():%Y%m%d}.xlsx"
        resp = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
    except Exception as e:
        traceback.print_exc()
        return json_err(f"양식 생성 오류: {str(e)}", status=500)
