# django_ma/partner/views.py
import json
import traceback
from datetime import datetime

import pandas as pd
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import StructureChange, PartnerChangeLog, StructureDeadline, SubAdminTemp


# ------------------------------------------------------------
# 공용 상수
# ------------------------------------------------------------
BRANCH_PARTS = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]


# ------------------------------------------------------------
# 📘 0. 기본 페이지 리디렉션
# ------------------------------------------------------------
@login_required
def redirect_to_calculate(request):
    """기본 수수료 페이지 접속 시 → 채권관리 페이지로 리다이렉트"""
    return redirect("manage_calculate")


@login_required
def manage_calculate(request):
    """지점효율 (제작중)"""
    return render(request, "partner/manage_calculate.html")


@login_required
def manage_rate(request):
    """요율관리 (제작중)"""
    return render(request, "partner/manage_rate.html")


# ------------------------------------------------------------
# 📘 1. 편제변경 메인 페이지
# ------------------------------------------------------------
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_charts(request):
    """편제변경 메인 페이지"""
    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"

    # 현재 로그인 사용자 branch 및 기한 조회
    user_branch = getattr(request.user, "branch", None)
    deadline_day = None
    if user_branch:
        deadline_day = (
            StructureDeadline.objects.filter(branch=user_branch, month=month_str)
            .values_list("deadline_day", flat=True)
            .first()
        )

    context = {
        "current_year": now.year,
        "current_month": now.month,
        "available_periods": [f"{now.year}-{m:02d}" for m in range(1, now.month + 1)],
        "future_select_until": (
            f"{now.year}-{now.month + 1:02d}"
            if now.month < 12
            else f"{now.year + 1}-01"
        ),
        "branches": BRANCH_PARTS,
        "deadline_day": deadline_day,
        "data_fetch_url": "/partner/api/fetch/",
        "data_save_url": "/partner/api/save/",
        "data_delete_url": "/partner/api/delete/",
        "set_deadline_url": "/partner/api/set-deadline/",
    }
    return render(request, "partner/manage_charts.html", context)


# ------------------------------------------------------------
# 📘 2. 편제변경 — 데이터 저장
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_save(request):
    """AJAX — 대상자 입력내용 저장"""
    try:
        payload = json.loads(request.body)
        items = payload.get("rows", [])
        month = payload.get("month")

        created_count = 0
        for row in items:
            target = CustomUser.objects.filter(id=row.get("tg_id")).first()
            StructureChange.objects.create(
                requester=request.user,
                target=target,
                branch=request.user.branch,
                target_branch=getattr(target, "branch", ""),
                chg_branch=row.get("chg_branch"),
                or_flag=row.get("or_flag", False),
                rank=row.get("tg_rank"),
                chg_rank=row.get("chg_rank"),
                table_name=row.get("tg_table"),
                chg_table=row.get("chg_table"),
                rate=row.get("tg_rate") or None,
                chg_rate=row.get("chg_rate") or None,
                memo=row.get("memo"),
                month=month,
            )
            created_count += 1

        PartnerChangeLog.objects.create(
            user=request.user,
            action="save",
            detail=f"{created_count}건 저장 (월도: {month})",
        )

        return JsonResponse({"status": "success", "message": f"{created_count}건 저장 완료"})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 3. 편제변경 — 데이터 삭제
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_delete(request):
    """AJAX — 행 삭제"""
    try:
        payload = json.loads(request.body)
        record = get_object_or_404(StructureChange, id=payload.get("id"))

        # 권한 체크
        if not (
            request.user.grade in ["superuser", "main_admin"]
            or record.requester == request.user
        ):
            return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)

        record.delete()
        PartnerChangeLog.objects.create(
            user=request.user,
            action="delete",
            detail=f"{record.id}번 레코드 삭제",
        )
        return JsonResponse({"status": "success", "message": "삭제 완료"})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 4. 편제변경 — 마감일 설정
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser"])
@transaction.atomic
def ajax_set_deadline(request):
    """AJAX — 입력기한 설정 및 저장"""
    try:
        payload = json.loads(request.body)
        branch = payload.get("branch")
        month = payload.get("month")
        deadline_day = payload.get("deadline_day")

        if not all([branch, month, deadline_day]):
            return JsonResponse({"status": "error", "message": "필수값 누락"}, status=400)

        obj, created = StructureDeadline.objects.update_or_create(
            branch=branch,
            month=month,
            defaults={"deadline_day": int(deadline_day)},
        )

        PartnerChangeLog.objects.create(
            user=request.user,
            action="set_deadline",
            detail=f"[{branch}] {month}월 기한 {deadline_day}일 {'등록' if created else '갱신'}",
        )

        return JsonResponse({
            "status": "success",
            "message": f"{branch} {month}월 기한 {deadline_day}일 {'등록' if created else '갱신'} 완료",
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 5. 편제변경 — 데이터 조회
# ------------------------------------------------------------
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_fetch(request):
    """AJAX — 월도 기준으로 편제변경 데이터 조회"""
    month = request.GET.get("month")
    if not month:
        return JsonResponse({"status": "success", "rows": []})

    qs = StructureChange.objects.filter(month=month).select_related("requester", "target")

    # 권한별 필터링
    user = request.user
    if user.grade == "main_admin":
        qs = qs.filter(branch=user.branch)
    elif user.grade == "sub_admin":
        qs = qs.filter(requester=user)

    rows = [
        {
            "id": obj.id,
            "requester_id": getattr(obj.requester, "id", ""),
            "requester_name": getattr(obj.requester, "name", ""),
            "branch": obj.branch,
            "target_id": getattr(obj.target, "id", ""),
            "target_name": getattr(obj.target, "name", ""),
            "target_branch": obj.target_branch,
            "chg_branch": obj.chg_branch,
            "rank": obj.rank,
            "chg_rank": obj.chg_rank,
            "table_name": obj.table_name,
            "chg_table": obj.chg_table,
            "rate": obj.rate,
            "chg_rate": obj.chg_rate,
            "memo": obj.memo,
            "request_date": obj.request_date.strftime("%Y-%m-%d") if obj.request_date else "",
            "process_date": obj.process_date.strftime("%Y-%m-%d") if obj.process_date else "",
        }
        for obj in qs
    ]
    return JsonResponse({"status": "success", "rows": rows})


# ------------------------------------------------------------
# 📘 6. 권한관리 페이지 (조회 전용 버전)
# ------------------------------------------------------------
# partner/views.py
@login_required
def manage_grades(request):
    """권한관리 페이지"""
    user = request.user
    selected_part = request.GET.get("part", "").strip() or None
    parts = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]

    # ✅ 중간관리자(SubAdminTemp)
    if user.grade == "superuser":
        if selected_part:
            subadmin_qs = SubAdminTemp.objects.filter(part=selected_part)
        else:
            subadmin_qs = SubAdminTemp.objects.none()  # 선택 전엔 빈 상태
    elif user.grade == "main_admin":
        subadmin_qs = SubAdminTemp.objects.filter(branch=user.branch)
    else:
        subadmin_qs = SubAdminTemp.objects.none()

    # ✅ 전체 사용자(CustomUser)
    if user.grade == "superuser":
        if selected_part:
            users_all = CustomUser.objects.filter(part=selected_part)
        else:
            users_all = CustomUser.objects.none()  # 선택 전엔 빈 상태
    elif user.grade == "main_admin":
        users_all = CustomUser.objects.filter(branch=user.branch)
    else:
        users_all = CustomUser.objects.none()

    empty_message_subadmin = ""
    if not subadmin_qs.exists():
        empty_message_subadmin = "표시할 중간관리자가 없습니다."

    return render(request, "partner/manage_grades.html", {
        "parts": parts,
        "selected_part": selected_part,
        "users_subadmin": subadmin_qs,
        "users_all": users_all,
        "empty_message_subadmin": empty_message_subadmin,
    })



# ------------------------------------------------------------
# 📘 7. 권한관리 — 엑셀 업로드 처리 (조회 외 유일 수정 기능)
# ------------------------------------------------------------
@transaction.atomic
@login_required
def upload_grades_excel(request):
    """
    엑셀 업로드를 통한 SubAdminTemp 업데이트
    - '사번', '팀A', '팀B', '팀C', '직급' 컬럼 사용
    """
    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]

        try:
            df = pd.read_excel(file).fillna("")

            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return redirect("partner:manage_grades")

            if "등급" in df.columns:
                df = df.drop(columns=["등급"])

            created, updated = 0, 0
            for _, row in df.iterrows():
                user_id = str(row["사번"]).strip()
                cu = CustomUser.objects.filter(id=user_id, grade="sub_admin").first()
                if not cu:
                    continue

                obj, is_created = SubAdminTemp.objects.update_or_create(
                    user=cu,
                    defaults={
                        "team_a": row["팀A"],
                        "team_b": row["팀B"],
                        "team_c": row["팀C"],
                        "position": row["직급"],
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

            messages.success(request, f"업로드 완료: 신규 {created}건, 수정 {updated}건")

        except Exception as e:
            messages.error(request, f"엑셀 처리 중 오류 발생: {e}")
    else:
        messages.warning(request, "엑셀 파일을 선택하세요.")

    return redirect("partner:manage_grades")


# ------------------------------------------------------------
# 📘 8. 권한관리 — 전체 사용자 Ajax 조회 (조회 전용)
# ------------------------------------------------------------
@login_required
def ajax_users_data(request):
    """
    DataTables 서버사이드 조회 전용
    ------------------------------------------------------------
    수정 불가, 조회 전용 버전
    ------------------------------------------------------------
    """
    user = request.user
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 10))
    search = request.GET.get("search[value]", "").strip()
    selected_part = request.GET.get("part", "").strip() or None

    if user.grade == "superuser":
        qs = CustomUser.objects.all()
        if selected_part:
            qs = qs.filter(part=selected_part)
    elif user.grade == "main_admin":
        qs = CustomUser.objects.filter(branch=user.branch)
    else:
        return JsonResponse({"data": [], "recordsTotal": 0, "recordsFiltered": 0})

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(id__icontains=search)
            | Q(branch__icontains=search)
            | Q(part__icontains=search)
        )

    total_count = qs.count()

    paginator = Paginator(qs.only("id", "name", "branch", "part", "grade")[:2000], length)
    page_number = start // length + 1
    page = paginator.get_page(page_number)

    subadmin_map = {
        str(sa.user_id): {
            "position": sa.position or "",
            "team_a": sa.team_a or "",
            "team_b": sa.team_b or "",
            "team_c": sa.team_c or "",
        }
        for sa in SubAdminTemp.objects.filter(user_id__in=[u.id for u in page])
    }

    data = []
    for u in page:
        sa_info = subadmin_map.get(str(u.id), {})
        data.append({
            "part": u.part or "-",
            "branch": u.branch or "-",
            "name": u.name or "-",
            "user_id": u.id,
            "position": sa_info.get("position", "-"),
            "team_a": sa_info.get("team_a", "-"),
            "team_b": sa_info.get("team_b", "-"),
            "team_c": sa_info.get("team_c", "-"),
        })

    return JsonResponse({
        "data": data,
        "recordsTotal": total_count,
        "recordsFiltered": total_count,
    })