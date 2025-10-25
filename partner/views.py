# django_ma/partner/views.py
import json
import traceback
from datetime import datetime

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
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
# 📘 6. 권한관리 페이지 (상단: subadmin / 하단: 전체 사용자)
# ------------------------------------------------------------
@login_required
def manage_grades(request):
    """
    권한관리 페이지
    - superuser: 선택한 부서(part) or 전체 조회
    - main_admin: 자신의 지점(branch) 기준으로만 조회
    - sub_admin 이하 등급은 접근 제한
    """
    user = request.user
    selected_part = request.GET.get("part", "").strip() or None
    parts = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]

    # ✅ 1️⃣ 조회 기준 구분
    if user.grade == "superuser":
        # superuser: 전체 or 선택한 부서만
        base_users = CustomUser.objects.filter(grade="sub_admin")
        if selected_part:
            base_users = base_users.filter(part=selected_part)

    elif user.grade == "main_admin":
        # main_admin: 자신의 지점(branch) 기준 sub_admin만
        if not user.branch:
            return render(request, "partner/manage_grades.html", {
                "parts": parts,
                "selected_part": selected_part,
                "users_subadmin": [],
                "users_all": [],
                "error_message": "지점 정보가 등록되지 않아 조회할 수 없습니다.",
            })
        base_users = CustomUser.objects.filter(branch=user.branch, grade="sub_admin")

    else:
        # 기타 권한은 접근 제한
        return render(request, "partner/manage_grades.html", {
            "parts": parts,
            "selected_part": selected_part,
            "users_subadmin": [],
            "users_all": [],
            "error_message": "접근 권한이 없습니다.",
        })

    # ✅ 2️⃣ SubAdminTemp 동기화
    for cu in base_users:
        SubAdminTemp.objects.get_or_create(
            user=cu,
            defaults={
                "name": cu.name,
                "part": cu.part,
                "branch": cu.branch,
            },
        )

    # ✅ 3️⃣ 상단: 중간관리자(SubAdminTemp)
    if user.grade == "superuser":
        users_subadmin = (
            SubAdminTemp.objects.filter(part=selected_part)
            if selected_part else SubAdminTemp.objects.all()
        )
    elif user.grade == "main_admin":
        users_subadmin = SubAdminTemp.objects.filter(branch=user.branch)
    else:
        users_subadmin = SubAdminTemp.objects.none()

    empty_message_subadmin = ""
    if not users_subadmin.exists():
        empty_message_subadmin = (
            "추가된 중간관리자가 없습니다.\n"
            "중간관리자 추가는 부서장에게 문의해주세요."
        )

    # ✅ 4️⃣ 하단: 전체 사용자 목록 (CustomUser + SubAdminTemp join)
    from django.db.models import Prefetch

    # SubAdminTemp 전체 미리 로드
    subadmin_qs = SubAdminTemp.objects.all()

    # 사용자 기본 쿼리
    if user.grade == "superuser":
        base_all = CustomUser.objects.all()
        if selected_part:
            base_all = base_all.filter(part=selected_part)
    elif user.grade == "main_admin":
        base_all = CustomUser.objects.filter(branch=user.branch)
    else:
        base_all = CustomUser.objects.none()

    # ✅ Prefetch + 매핑 처리
    users_all = (
        base_all
        .prefetch_related(Prefetch("subadmin_detail", queryset=subadmin_qs))
        .order_by("name")
    )

    # ✅ 5️⃣ 렌더링
    return render(request, "partner/manage_grades.html", {
        "parts": parts,
        "selected_part": selected_part,
        "users_subadmin": users_subadmin,
        "users_all": users_all,
        "empty_message_subadmin": empty_message_subadmin,
    })


# ------------------------------------------------------------
# 📘 7. 권한관리 — 엑셀 업로드 처리 (grade 비노출)
# ------------------------------------------------------------
@transaction.atomic
@login_required
def upload_grades_excel(request):
    """
    엑셀 업로드를 통한 SubAdminTemp 업데이트
    - '사번', '팀A', '팀B', '팀C', '직급' 컬럼 사용
    - '등급' 컬럼이 있더라도 무시 (비노출 정책)
    """
    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]

        try:
            import pandas as pd
            df = pd.read_excel(file).fillna("")

            # ✅ 필수 컬럼 검증
            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return redirect("partner:manage_grades")

            # ✅ 불필요한 '등급' 컬럼은 제거 (있어도 무시)
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
                        # level은 grade와 독립 → 선택적으로 나중 확장 가능
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
# 📘 8. 권한관리 — 팀A/B/C 실시간 수정
# ------------------------------------------------------------
@require_POST
@login_required
def ajax_update_team(request):
    """팀A/B/C 인라인 수정 처리 (AJAX)"""
    try:
        user_id = request.POST.get("user_id")
        field = request.POST.get("field")
        value = request.POST.get("value", "").strip()

        if field not in ["team_a", "team_b", "team_c"]:
            return JsonResponse({"success": False, "error": "Invalid field"}, status=400)

        cu = CustomUser.objects.filter(id=user_id).first()
        if not cu:
            return JsonResponse({"success": False, "error": "User not found"}, status=404)

        obj, _ = SubAdminTemp.objects.get_or_create(
            user=cu,
            defaults={
                "name": cu.name,
                "part": cu.part,
                "branch": cu.branch,
            },
        )
        setattr(obj, field, value)
        obj.save(update_fields=[field, "updated_at"])

        return JsonResponse({"success": True, "message": f"{field} 업데이트 완료"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

