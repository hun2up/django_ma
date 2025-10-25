# django_ma/partner/views.py
import json
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import StructureChange, PartnerChangeLog, StructureDeadline



# ✅ 기본 수수료 페이지 접속 시 → 채권관리 페이지로 자동 이동
def redirect_to_calculate(request):
    return redirect('manage_calculate')

# Create your views here.
# ✅ 권한관리 (제작중)
def manage_grades(request):
    return render(request, 'partner/manage_grades.html')


# ✅ 지점효율 (제작중)
def manage_calculate(request):
    return render(request, 'partner/manage_calculate.html')


# ============================================================
# 📘 1. 메인 페이지
# ============================================================
@grade_required(['superuser', 'main_admin', 'sub_admin'])
def manage_charts(request):
    """편제변경 메인 페이지"""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    month_str = f"{current_year}-{current_month:02d}"

    # ✅ 현재 로그인 사용자의 branch 가져오기
    user_branch = getattr(request.user, "branch", None)

    # ✅ 현재월 기준 기한 불러오기
    deadline_day = None
    if user_branch:
        deadline_day = (
            StructureDeadline.objects.filter(branch=user_branch, month=month_str)
            .values_list("deadline_day", flat=True)
            .first()
        )

    context = {
        "current_year": current_year,
        "current_month": current_month,
        "available_periods": [f"{current_year}-{m:02d}" for m in range(1, current_month + 1)],
        "future_select_until": f"{current_year}-{current_month + 1:02d}" if current_month < 12 else f"{current_year + 1}-01",
        "branches": ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"],

        # ✅ 현재월 기준 실제 기한값 전달
        "deadline_day": deadline_day if deadline_day else None,

        "data_fetch_url": "/partner/api/fetch/",
        "data_save_url": "/partner/api/save/",
        "data_delete_url": "/partner/api/delete/",
        "set_deadline_url": "/partner/api/set-deadline/",
    }
    return render(request, "partner/manage_charts.html", context)


# ============================================================
# 📘 2. 데이터 저장 (입력행 저장)
# ============================================================
@require_POST
@grade_required(['superuser', 'main_admin', 'sub_admin'])
@transaction.atomic
def ajax_save(request):
    """대상자 입력내용 저장"""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        items = payload.get("rows", [])
        month = payload.get("month")

        created_count = 0
        for row in items:
            target_id = row.get("tg_id")
            target = CustomUser.objects.filter(id=target_id).first()
            requester = request.user

            StructureChange.objects.create(
                requester=requester,
                target=target,
                branch=requester.branch,
                target_branch=target.branch if target else "",
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
            detail=f"{created_count}건 저장 (월도: {month})"
        )
        return JsonResponse({"status": "success", "message": f"{created_count}건 저장 완료"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ============================================================
# 📘 3. 데이터 삭제
# ============================================================
@require_POST
@grade_required(['superuser', 'main_admin', 'sub_admin'])
@transaction.atomic
def ajax_delete(request):
    """행 삭제"""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        record_id = payload.get("id")
        record = get_object_or_404(StructureChange, id=record_id)

        # 권한 체크
        if not (request.user.grade in ["superuser", "main_admin"] or record.requester == request.user):
            return JsonResponse({"status": "error", "message": "삭제 권한이 없습니다."}, status=403)

        record.delete()
        PartnerChangeLog.objects.create(
            user=request.user,
            action="delete",
            detail=f"{record_id}번 레코드 삭제"
        )
        return JsonResponse({"status": "success", "message": "삭제 완료"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ============================================================
# 📘 4. 입력기한 설정
# ============================================================
@require_POST
@grade_required(['superuser'])
@transaction.atomic
def ajax_set_deadline(request):
    """입력기한 설정 및 DB 저장"""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        branch = payload.get("branch")
        deadline_day = payload.get("deadline_day")
        month = payload.get("month")

        if not all([branch, deadline_day, month]):
            return JsonResponse({"status": "error", "message": "필수값 누락"}, status=400)

        # ✅ StructureDeadline 테이블에 저장 (없으면 생성)
        obj, created = StructureDeadline.objects.update_or_create(
            branch=branch,
            month=month,
            defaults={"deadline_day": int(deadline_day)},
        )

        # ✅ 로그 기록
        PartnerChangeLog.objects.create(
            user=request.user,
            action="set_deadline",
            detail=f"[{branch}] {month}월 기한 {deadline_day}일 {'등록' if created else '갱신'}"
        )

        return JsonResponse({
            "status": "success",
            "message": f"{branch} {month}월 기한 {deadline_day}일 {'등록' if created else '갱신'} 완료"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ============================================================
# 📘 5. 데이터 조회 (ajax_fetch)
# ============================================================

@grade_required(['superuser', 'main_admin', 'sub_admin'])
def ajax_fetch(request):
    """월도 기준으로 편제변경 데이터 조회"""
    month = request.GET.get("month")
    if not month:
        return JsonResponse({"status": "success", "rows": []})

    # 기본 쿼리
    qs = StructureChange.objects.filter(month=month).select_related("requester", "target")

    # 권한별 필터링
    user = request.user
    if user.grade == "main_admin":
        qs = qs.filter(branch=user.branch)
    elif user.grade == "sub_admin":
        qs = qs.filter(requester=user)

    # JSON 직렬화
    rows = []
    for obj in qs:
        rows.append({
            "id": obj.id,
            "requester_id": obj.requester.id if obj.requester else "",
            "requester_name": obj.requester.name if obj.requester else "",
            "branch": obj.branch,
            "target_id": obj.target.id if obj.target else "",
            "target_name": obj.target.name if obj.target else "",
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
        })

    return JsonResponse({"status": "success", "rows": rows})
