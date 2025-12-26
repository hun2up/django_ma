# django_ma/partner/views.py

import io
import json
import traceback
from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import (
    PartnerChangeLog,
    RateChange,
    RateTable,
    StructureChange,
    SubAdminTemp,
    TableSetting,
)

# ------------------------------------------------------------
# 공용 상수
# ------------------------------------------------------------
BRANCH_PARTS = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부", "MA사업5부"]


# ------------------------------------------------------------
# 공용 유틸
# ------------------------------------------------------------
def normalize_month(month: str) -> str:
    month = (month or "").strip()
    if not month:
        return ""
    if "-" in month:
        try:
            y, m = month.split("-")
            return f"{y}-{int(m):02d}"
        except Exception:
            return month
    # 혹시 202501 같은 값이 오면 보정
    digits = "".join([c for c in month if c.isdigit()])
    if len(digits) == 6:
        return f"{digits[:4]}-{digits[4:6]}"
    return month


def parse_yyyy_mm_dd_or_none(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return datetime.strptime(v, "%Y-%m-%d").date()


def build_affiliation_display(user: CustomUser) -> str:
    """
    표기 규칙:
    - team_a가 없거나 '-'면: user.branch 표기
    - team_a가 있으면: 'team_a team_b team_c' (단, team_b/team_c가 '-'면 제외)
    """
    def clean(x: str) -> str:
        x = (x or "").strip()
        return "" if x == "-" else x

    branch = clean(getattr(user, "branch", "")) or "-"

    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return branch

    team_a = clean(getattr(sa, "team_a", ""))
    team_b = clean(getattr(sa, "team_b", ""))
    team_c = clean(getattr(sa, "team_c", ""))

    if not team_a:
        return branch

    parts = [p for p in [team_a, team_b, team_c] if p]
    return " ".join(parts) if parts else branch


def find_table_rate(branch: str, table_name: str) -> str:
    if not table_name:
        return ""
    ts = (
        TableSetting.objects.filter(branch=branch, table_name=table_name)
        .order_by("order")
        .first()
    )
    return (ts.rate or "") if ts else ""


# ------------------------------------------------------------
# Pages
# ------------------------------------------------------------
@login_required
def redirect_to_calculate(request):
    return redirect("partner:manage_calculate")


@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_calculate(request):
    return render(request, "partner/manage_calculate.html")


@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_rate(request):
    now = datetime.now()
    user = request.user
    subadmin_info = SubAdminTemp.objects.filter(user=user).first()

    context = {
        "current_year": now.year,
        "current_month": now.month,
        "selected_year": now.year,
        "selected_month": now.month,
        "auto_load": True,

        # ✅ 템플릿에서 subadmin_info를 쓰고 있음(누락되면 data- 속성들이 비거나 에러)
        "subadmin_info": subadmin_info,

        # ✅ JS가 참조할 URL들
        "data_fetch_url": reverse("partner:rate_fetch"),
        "data_save_url": reverse("partner:rate_save"),
        "data_delete_url": reverse("partner:rate_delete"),

        # ✅ 처리일자 업데이트 URL(요율 전용 alias 권장)
        "update_process_date_url": reverse("partner:ajax_update_process_date"),
    }
    return render(request, "partner/manage_rate.html", context)


@login_required
@grade_required(["superuser", "main_admin"])
def manage_tables(request):
    return render(request, "partner/manage_tables.html")


@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_charts(request):
    now = datetime.now()
    user = request.user

    selected_branch = None
    if user.grade == "main_admin" and user.branch:
        selected_branch = user.branch

    subadmin_info = SubAdminTemp.objects.filter(user=user).first()

    context = {
        "current_year": now.year,
        "current_month": now.month,
        "selected_year": now.year,
        "selected_month": now.month,
        "branches": BRANCH_PARTS,
        "selected_branch": selected_branch,

        # ✅ 가능하면 reverse로 통일(하지만 기존 JS 호환 위해 legacy도 유지)
        "data_fetch_url": reverse("partner:structure_fetch"),
        "data_save_url": reverse("partner:structure_save"),
        "data_delete_url": reverse("partner:structure_delete"),
        "update_process_date_url": reverse("partner:structure_update_process_date"),

        "auto_load": user.grade in ["main_admin", "sub_admin"],
        "subadmin_info": subadmin_info,
    }
    return render(request, "partner/manage_charts.html", context)


# ------------------------------------------------------------
# Structure (편제) - 공용 save/delete/fetch
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_save(request):
    try:
        payload = json.loads(request.body or "{}")
        items = payload.get("rows", [])
        month = normalize_month(payload.get("month") or "")

        user = request.user
        part = (payload.get("part") or getattr(user, "part", "") or "-").strip()
        branch = (payload.get("branch") or getattr(user, "branch", "") or "-").strip()
        if user.grade in ["main_admin", "sub_admin"]:
            branch = (getattr(user, "branch", "") or branch).strip()

        created_count = 0
        for row in items:
            target_id = str(row.get("target_id") or "").strip()
            if not target_id:
                continue

            target = CustomUser.objects.filter(id=target_id).first()
            if not target:
                continue

            display_branch = build_affiliation_display(target)

            StructureChange.objects.create(
                requester=user,
                target=target,
                part=part,
                branch=branch,
                month=month,

                target_branch=display_branch,
                chg_branch=(row.get("chg_branch") or "-").strip() or "-",
                or_flag=bool(row.get("or_flag", False)),
                rank=(row.get("tg_rank") or "-").strip() or "-",
                chg_rank=(row.get("chg_rank") or "-").strip() or "-",
                memo=(row.get("memo") or "").strip(),
            )
            created_count += 1

        PartnerChangeLog.objects.create(
            user=user,
            action="save",
            detail=f"{created_count}건 저장 (structure / 월도:{month} / 부서:{part} / 지점:{branch})",
        )
        return JsonResponse({"status": "success", "saved_count": created_count})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_delete(request):
    try:
        data = json.loads(request.body or "{}")
        record_id = data.get("id")
        if not record_id:
            return JsonResponse({"status": "error", "message": "id 누락"}, status=400)

        record = get_object_or_404(StructureChange, id=record_id)
        user = request.user

        if not (user.grade in ["superuser", "main_admin"] or record.requester_id == user.id):
            return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)

        deleted_id = record.id
        record.delete()

        PartnerChangeLog.objects.create(
            user=user, action="delete", detail=f"StructureChange #{deleted_id} 삭제"
        )
        return JsonResponse({"status": "success", "message": f"#{deleted_id} 삭제 완료"})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_fetch(request):
    try:
        user = request.user
        month = normalize_month(request.GET.get("month") or "")
        branch = (request.GET.get("branch") or "").strip()

        qs = StructureChange.objects.filter(month=month).select_related("requester", "target")

        if user.grade == "superuser":
            if branch:
                qs = qs.filter(branch__iexact=branch)
        else:
            qs = qs.filter(branch__iexact=user.branch)

        rows = []
        for sc in qs:
            rows.append(
                {
                    "id": sc.id,
                    "requester_id": getattr(sc.requester, "id", ""),
                    "requester_name": getattr(sc.requester, "name", ""),
                    "requester_branch": build_affiliation_display(sc.requester),
                    "target_id": getattr(sc.target, "id", ""),
                    "target_name": getattr(sc.target, "name", ""),
                    "target_branch": sc.target_branch or "",
                    "chg_branch": sc.chg_branch or "",
                    "rank": sc.rank or "",
                    "chg_rank": sc.chg_rank or "",
                    "or_flag": bool(sc.or_flag),
                    "memo": sc.memo or "",
                    "request_date": sc.created_at.strftime("%Y-%m-%d") if sc.created_at else "",
                    "process_date": sc.process_date.strftime("%Y-%m-%d") if sc.process_date else "",
                }
            )

        return JsonResponse({"status": "success", "rows": rows})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e), "rows": []}, status=500)


# ------------------------------------------------------------
# 처리일자 수정(편제/요율 공용) - ✅ 핵심
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def ajax_update_process_date(request):
    """AJAX — 메인시트 처리일자 수정 (편제/요율 공용)"""
    try:
        payload = json.loads(request.body or "{}")

        record_id = payload.get("id")
        new_date = (payload.get("process_date") or "").strip()
        kind = (payload.get("type") or payload.get("kind") or "structure").strip().lower()  # rate|structure

        if not record_id:
            return JsonResponse({"status": "error", "message": "id 누락"}, status=400)

        # 빈값이면 None 처리(삭제)
        if new_date == "":
            parsed_date = None
        else:
            try:
                parsed_date = parse_yyyy_mm_dd_or_none(new_date)
            except ValueError:
                return JsonResponse(
                    {"status": "error", "message": "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)"},
                    status=400,
                )

        if kind == "rate":
            record = get_object_or_404(RateChange, id=record_id)
        else:
            record = get_object_or_404(StructureChange, id=record_id)

        record.process_date = parsed_date
        record.save(update_fields=["process_date"])

        PartnerChangeLog.objects.create(
            user=request.user,
            action="update_process_date",
            detail=f"[{kind}] ID {record_id} 처리일자 수정 → {new_date or 'NULL'}",
        )

        return JsonResponse({
            "status": "success",
            "message": "처리일자 변경 완료",
            "process_date": new_date,  # 프론트 동기화용
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 권한관리
# ------------------------------------------------------------
@login_required
@grade_required(["superuser", "main_admin"])
def manage_grades(request):
    user = request.user
    selected_part = (request.GET.get("part") or "").strip() or None
    parts = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]

    base_sub_admin_users = CustomUser.objects.filter(grade="sub_admin")

    if user.grade == "superuser":
        subadmin_qs = (
            SubAdminTemp.objects.filter(part=selected_part, user__in=base_sub_admin_users)
            if selected_part
            else SubAdminTemp.objects.none()
        )
        users_all = (
            CustomUser.objects.filter(part=selected_part)
            if selected_part
            else CustomUser.objects.none()
        )
    else:
        selected_part = user.branch
        subadmin_qs = SubAdminTemp.objects.filter(branch=user.branch, user__in=base_sub_admin_users)
        users_all = CustomUser.objects.filter(branch=user.branch)

    empty_message_subadmin = "" if subadmin_qs.exists() else "표시할 중간관리자가 없습니다."
    LEVELS = ["-", "A레벨", "B레벨", "C레벨"]

    return render(
        request,
        "partner/manage_grades.html",
        {
            "parts": parts,
            "selected_part": selected_part,
            "users_subadmin": subadmin_qs,
            "users_all": users_all,
            "empty_message_subadmin": empty_message_subadmin,
            "levels": LEVELS,
        },
    )


@transaction.atomic
@login_required
def upload_grades_excel(request):
    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(file, sheet_name="업로드").fillna("")
            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return redirect("partner:manage_grades")

            for col in ["부서", "지점", "등급"]:
                if col in df.columns:
                    df = df.drop(columns=[col])

            updated, created = 0, 0
            for _, row in df.iterrows():
                user_id = str(row["사번"]).strip()
                cu = CustomUser.objects.filter(id=user_id).first()
                if not cu:
                    continue

                _, is_created = SubAdminTemp.objects.update_or_create(
                    user=cu,
                    defaults={
                        "part": cu.part or "-",
                        "branch": cu.branch or "-",
                        "name": cu.name or "-",
                        "team_a": row["팀A"] or "-",
                        "team_b": row["팀B"] or "-",
                        "team_c": row["팀C"] or "-",
                        "position": row["직급"] or "-",
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

            messages.success(request, f"업로드 완료: 신규 {created}건, 수정 {updated}건 반영")

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"엑셀 처리 중 오류 발생: {e}")
    else:
        messages.warning(request, "엑셀 파일을 선택하세요.")

    return redirect("partner:manage_grades")


@login_required
def ajax_users_data(request):
    user = request.user

    try:
        start = max(int(request.GET.get("start", 0)), 0)
    except ValueError:
        start = 0

    try:
        length = int(request.GET.get("length", 10))
        if length <= 0:
            length = 10
    except ValueError:
        length = 10

    search = (request.GET.get("search[value]", "") or "").strip()
    selected_part = (request.GET.get("part", "") or "").strip() or None

    if user.grade == "superuser":
        base_qs = CustomUser.objects.all()
        if selected_part:
            base_qs = base_qs.filter(part=selected_part)
    elif user.grade == "main_admin":
        base_qs = CustomUser.objects.filter(branch=user.branch)
    else:
        return JsonResponse({"data": [], "recordsTotal": 0, "recordsFiltered": 0})

    records_total = base_qs.count()
    qs = base_qs

    if search:
        ids_from_custom = list(
            qs.filter(
                Q(name__icontains=search)
                | Q(id__icontains=search)
                | Q(branch__icontains=search)
                | Q(part__icontains=search)
            ).values_list("id", flat=True)
        )
        ids_from_subadmin = list(
            SubAdminTemp.objects.filter(
                Q(team_a__icontains=search)
                | Q(team_b__icontains=search)
                | Q(team_c__icontains=search)
                | Q(position__icontains=search)
            ).values_list("user_id", flat=True)
        )
        combined_ids = set(ids_from_custom) | set(ids_from_subadmin)
        qs = qs.filter(id__in=combined_ids)

    records_filtered = qs.count()
    qs = qs.order_by("name", "id")
    page_qs = qs.only("id", "name", "branch", "part")[start : start + length]

    page_ids = [u.id for u in page_qs]
    subadmin_map = {
        str(sa.user_id): {
            "position": sa.position or "-",
            "team_a": sa.team_a or "-",
            "team_b": sa.team_b or "-",
            "team_c": sa.team_c or "-",
        }
        for sa in SubAdminTemp.objects.filter(user_id__in=page_ids)
    }

    data = []
    for u in page_qs:
        sa = subadmin_map.get(str(u.id), {})
        data.append(
            {
                "part": u.part or "-",
                "branch": u.branch or "-",
                "name": u.name or "-",
                "user_id": u.id,
                "position": sa.get("position", "-"),
                "team_a": sa.get("team_a", "-"),
                "team_b": sa.get("team_b", "-"),
                "team_c": sa.get("team_c", "-"),
            }
        )

    return JsonResponse({"data": data, "recordsTotal": records_total, "recordsFiltered": records_filtered})


@require_POST
@login_required
@grade_required(["superuser", "main_admin"])
def ajax_update_level(request):
    user_id = request.POST.get("user_id")
    level = request.POST.get("level")

    try:
        sub_admin = SubAdminTemp.objects.get(user_id=user_id)
        sub_admin.level = level
        sub_admin.save()
        return JsonResponse({"success": True})
    except SubAdminTemp.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})


@login_required
@grade_required(["superuser"])
def ajax_fetch_parts(request):
    exclude_list = ["1인GA사업부", "MA사업0부"]
    parts = (
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
        .exclude(part__in=exclude_list)
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )
    return JsonResponse({"parts": list(parts)})


@login_required
@grade_required(["superuser"])
def ajax_fetch_branches(request):
    part = request.GET.get("part")
    if not part:
        return JsonResponse({"branches": []})

    branches = (
        CustomUser.objects.filter(part__iexact=part)
        .exclude(branch__isnull=True)
        .exclude(branch__exact="")
        .values_list("branch", flat=True)
        .distinct()
        .order_by("branch")
    )
    return JsonResponse({"branches": list(branches)})


# ------------------------------------------------------------
# TableSetting
# ------------------------------------------------------------
@require_GET
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_table_fetch(request):
    branch = (request.GET.get("branch") or "").strip()
    user = request.user

    if not branch:
        return JsonResponse({"status": "error", "message": "지점(branch) 정보가 없습니다."})

    if user.grade != "superuser" and branch != user.branch:
        return JsonResponse({"status": "error", "message": "다른 지점 테이블에는 접근할 수 없습니다."})

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
        return JsonResponse({"status": "success", "rows": data})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": f"조회 중 오류 발생: {str(e)}"})


@require_POST
@login_required
@grade_required(["superuser", "main_admin"])
def ajax_table_save(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        branch = data.get("branch")
        rows = data.get("rows", [])

        if not branch or not isinstance(rows, list):
            return JsonResponse({"status": "error", "message": "요청 데이터가 잘못되었습니다."})

        with transaction.atomic():
            TableSetting.objects.filter(branch=branch).delete()

            objs = []
            for r in rows:
                order = int(r.get("order") or 0)
                table_name = (r.get("table") or "").strip()
                rate = (r.get("rate") or "").strip()
                if not table_name and not rate:
                    continue

                objs.append(
                    TableSetting(branch=branch, table_name=table_name, rate=rate, order=order)
                )

            TableSetting.objects.bulk_create(objs)

        return JsonResponse({"status": "success", "saved_count": len(objs)})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)})


# ------------------------------------------------------------
# RateTable(요율현황)
# ------------------------------------------------------------
@require_GET
@login_required
def ajax_rate_userlist(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"data": []})

    users = (
        CustomUser.objects.filter(branch=branch, is_active=True)
        .values("id", "name", "branch")
        .order_by("name")
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


@login_required
def ajax_rate_userlist_excel(request):
    branch = (request.GET.get("branch") or "").strip()
    if not branch:
        return JsonResponse({"error": "지점을 선택해주세요."}, status=400)

    user = request.user
    if user.grade != "superuser" and branch != user.branch:
        return JsonResponse({"error": "다른 지점 데이터에는 접근할 수 없습니다."}, status=403)

    users = list(
        CustomUser.objects.filter(branch=branch, is_active=True)
        .values("id", "name", "branch")
        .order_by("name")
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
@login_required
@transaction.atomic
def ajax_rate_userlist_upload(request):
    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        return JsonResponse({"status": "error", "message": "엑셀 파일이 없습니다."}, status=400)

    try:
        file_path = default_storage.save(f"tmp/{excel_file.name}", excel_file)
        file_path_full = default_storage.path(file_path)
        df = pd.read_excel(file_path_full, sheet_name="업로드").fillna("")

        required_cols = ["사번", "손보테이블", "생보테이블"]
        for col in required_cols:
            if col not in df.columns:
                return JsonResponse({"status": "error", "message": f"'{col}' 컬럼이 없습니다."}, status=400)

        updated_count, skipped_count = 0, 0

        for _, row in df.iterrows():
            user_id = str(row["사번"]).strip()
            if not user_id:
                skipped_count += 1
                continue

            user = CustomUser.objects.filter(id=user_id).first()
            if not user:
                skipped_count += 1
                continue

            RateTable.objects.update_or_create(
                user=user,
                defaults={"non_life_table": row["손보테이블"], "life_table": row["생보테이블"]},
            )
            updated_count += 1

        default_storage.delete(file_path)

        return JsonResponse(
            {"status": "success", "message": f"업로드 완료 ({updated_count}건 업데이트 / {skipped_count}건 스킵됨)"}
        )

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": f"업로드 중 오류: {str(e)}"}, status=500)


@require_GET
@login_required
def ajax_rate_user_detail(request):
    user_id = (request.GET.get("user_id") or "").strip()
    if not user_id:
        return JsonResponse({"status": "error", "message": "user_id가 없습니다."}, status=400)

    try:
        target = CustomUser.objects.get(id=user_id)

        rate_info = RateTable.objects.filter(user=target).first()
        non_life_table = rate_info.non_life_table if rate_info else ""
        life_table = rate_info.life_table if rate_info else ""

        non_life_rate = find_table_rate(target.branch, non_life_table)
        life_rate = find_table_rate(target.branch, life_table)

        return JsonResponse(
            {
                "status": "success",
                "data": {
                    "target_name": target.name,
                    "target_id": target.id,
                    "non_life_table": non_life_table,
                    "life_table": life_table,
                    "non_life_rate": non_life_rate,
                    "life_rate": life_rate,
                    "branch": target.branch or "",
                },
            }
        )

    except CustomUser.DoesNotExist:
        return JsonResponse({"status": "error", "message": "대상자를 찾을 수 없습니다."}, status=404)
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# ------------------------------------------------------------
# RateChange (요율변경)
# ------------------------------------------------------------
@require_GET
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def rate_fetch(request):
    user = request.user
    month = normalize_month(request.GET.get("month") or "")
    branch = (request.GET.get("branch") or "").strip()

    qs = RateChange.objects.filter(month=month).select_related("requester", "target")

    if user.grade == "superuser":
        if branch:
            qs = qs.filter(branch__iexact=branch)
    else:
        qs = qs.filter(branch__iexact=user.branch)

    rows = []
    for rc in qs:
        rows.append(
            {
                "id": rc.id,
                "requester_name": rc.requester.name,
                "requester_id": rc.requester.id,
                "target_name": rc.target.name,
                "target_id": rc.target.id,

                "before_ftable": rc.before_ftable,
                "before_frate": rc.before_frate,
                "after_ftable": rc.after_ftable,
                "after_frate": rc.after_frate,

                "before_ltable": rc.before_ltable,
                "before_lrate": rc.before_lrate,
                "after_ltable": rc.after_ltable,
                "after_lrate": rc.after_lrate,

                "memo": rc.memo,
                "request_date": rc.created_at.strftime("%Y-%m-%d") if rc.created_at else "",
                "process_date": rc.process_date.strftime("%Y-%m-%d") if rc.process_date else "",
            }
        )

    return JsonResponse({"status": "success", "kind": "rate", "rows": rows})


@require_POST
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def rate_save(request):
    payload = json.loads(request.body or "{}")
    rows = payload.get("rows", [])
    month = normalize_month(payload.get("month") or "")

    user = request.user
    part = (payload.get("part") or getattr(user, "part", "") or "-").strip()
    branch = (payload.get("branch") or getattr(user, "branch", "") or "-").strip()
    if user.grade in ["main_admin", "sub_admin"]:
        branch = (getattr(user, "branch", "") or branch).strip()

    saved = 0
    for r in rows:
        target_id = str(r.get("target_id") or "").strip()
        if not target_id:
            continue

        target = CustomUser.objects.filter(id=target_id).first()
        if not target:
            continue

        rt = RateTable.objects.filter(user=target).first()
        before_ftable = rt.non_life_table if rt else ""
        before_ltable = rt.life_table if rt else ""

        before_frate = find_table_rate(target.branch, before_ftable)
        before_lrate = find_table_rate(target.branch, before_ltable)

        after_ftable = (r.get("after_ftable") or "").strip()
        after_ltable = (r.get("after_ltable") or "").strip()

        after_frate = find_table_rate(target.branch, after_ftable)
        after_lrate = find_table_rate(target.branch, after_ltable)

        memo = (r.get("memo") or "").strip()

        RateChange.objects.create(
            requester=user,
            target=target,
            part=part,
            branch=branch,
            month=month,

            before_ftable=before_ftable,
            before_frate=before_frate,
            before_ltable=before_ltable,
            before_lrate=before_lrate,

            after_ftable=after_ftable,
            after_frate=after_frate,
            after_ltable=after_ltable,
            after_lrate=after_lrate,

            memo=memo,
        )
        saved += 1

    return JsonResponse({"status": "success", "saved_count": saved})


@require_POST
@login_required
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def rate_delete(request):
    data = json.loads(request.body or "{}")
    record_id = data.get("id")
    if not record_id:
        return JsonResponse({"status": "error", "message": "id 누락"}, status=400)

    rc = get_object_or_404(RateChange, id=record_id)
    user = request.user

    if not (user.grade in ["superuser", "main_admin"] or rc.requester_id == user.id):
        return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)

    rc.delete()
    return JsonResponse({"status": "success"})


# ------------------------------------------------------------
# Structure endpoints (전용 alias)
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def structure_fetch(request):
    return ajax_fetch(request)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def structure_save(request):
    return ajax_save(request)


@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def structure_delete(request):
    return ajax_delete(request)
