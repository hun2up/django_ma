# django_ma/partner/views/grades.py
# ------------------------------------------------------------
# ✅ Permission Management (manage_grades + excel upload + datatables api + level update)
# ------------------------------------------------------------

import traceback

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from partner.models import SubAdminTemp

from .constants import BRANCH_PARTS
from .utils import find_part_by_branch


@login_required
@grade_required("superuser", "head")
def manage_grades(request):
    user = request.user
    LEVELS = ["-", "A레벨", "B레벨", "C레벨"]
    parts = sorted(list(BRANCH_PARTS.keys()))

    selected_channel = (request.GET.get("channel") or "").strip()
    selected_part = (request.GET.get("part") or "").strip()
    selected_branch = (request.GET.get("branch") or "").strip()

    base_leader_users = CustomUser.objects.filter(grade="leader")

    if user.grade == "superuser":
        if selected_channel and selected_part and selected_branch:
            subadmin_qs = SubAdminTemp.objects.filter(
                part=selected_part,
                branch=selected_branch,
                user__in=base_leader_users,
            )
            users_all = CustomUser.objects.filter(
                channel=selected_channel,
                part=selected_part,
                branch=selected_branch,
            )
        else:
            subadmin_qs = SubAdminTemp.objects.none()
            users_all = CustomUser.objects.none()
    else:
        selected_branch = (user.branch or "").strip()
        selected_part = find_part_by_branch(selected_branch) or (user.part or "").strip()

        subadmin_qs = SubAdminTemp.objects.filter(branch=selected_branch, user__in=base_leader_users)
        users_all = CustomUser.objects.filter(branch=selected_branch)

    empty_message_subadmin = "" if subadmin_qs.exists() else "표시할 중간관리자가 없습니다."

    return render(
        request,
        "partner/manage_grades.html",
        {
            "parts": parts,
            "selected_channel": selected_channel or None,
            "selected_part": selected_part or None,
            "selected_branch": selected_branch or None,
            "users_subadmin": subadmin_qs,
            "users_all": users_all,
            "empty_message_subadmin": empty_message_subadmin,
            "levels": LEVELS,
        },
    )


@transaction.atomic
@login_required
@grade_required("superuser", "head")
def upload_grades_excel(request):
    redirect_part = (request.GET.get("part") or "").strip()
    redirect_branch = (request.GET.get("branch") or "").strip()

    def _redirect():
        qs = []
        if redirect_part:
            qs.append(f"part={redirect_part}")
        if redirect_branch:
            qs.append(f"branch={redirect_branch}")
        base = reverse("partner:manage_grades")
        return redirect(f"{base}?{'&'.join(qs)}" if qs else base)

    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(file, sheet_name="업로드").fillna("")
            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return _redirect()

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
                created += 1 if is_created else 0
                updated += 0 if is_created else 1

            messages.success(request, f"업로드 완료: 신규 {created}건, 수정 {updated}건 반영")
        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"엑셀 처리 중 오류 발생: {e}")
    else:
        messages.warning(request, "엑셀 파일을 선택하세요.")

    return _redirect()


@login_required
@grade_required("superuser", "head")
def ajax_users_data(request):
    """✅ DataTables server-side API"""
    user = request.user

    try:
        draw = int(request.GET.get("draw", "1") or "1")
    except ValueError:
        draw = 1

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
    selected_part = (request.GET.get("part", "") or "").strip()
    selected_branch = (request.GET.get("branch", "") or "").strip()

    try:
        if user.grade == "superuser":
            if not selected_part or not selected_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)
            base_qs = CustomUser.objects.filter(part=selected_part, branch=selected_branch)
        else:
            fixed_branch = (user.branch or "").strip()
            if not fixed_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)
            base_qs = CustomUser.objects.filter(branch=fixed_branch)
            if not selected_part:
                selected_part = find_part_by_branch(fixed_branch) or (user.part or "").strip()

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

        return JsonResponse(
            {"draw": draw, "data": data, "recordsTotal": records_total, "recordsFiltered": records_filtered},
            status=200,
        )

    except Exception as e:
        traceback.print_exc()
        return JsonResponse(
            {"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0, "error": str(e)},
            status=200,
        )


@require_POST
@login_required
@grade_required("superuser", "head")
def ajax_update_level(request):
    user_id = request.POST.get("user_id")
    level = request.POST.get("level")
    try:
        leader = SubAdminTemp.objects.get(user_id=user_id)
        leader.level = level
        leader.save(update_fields=["level"])
        return JsonResponse({"success": True})
    except SubAdminTemp.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})
