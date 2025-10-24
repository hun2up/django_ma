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
from .models import StructureChange, PartnerChangeLog



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
    context = {
        "current_year": now.year,
        "current_month": now.month,
        "available_periods": [f"{now.year}-{m:02d}" for m in range(1, now.month + 1)],  # 예시용
        "future_select_until": f"{now.year}-{now.month + 1:02d}" if now.month < 12 else f"{now.year + 1}-01",
        "branches": ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"],
        "deadline_day": None,
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
    """입력기한 설정"""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        branch = payload.get("branch")
        deadline_day = payload.get("deadline_day")
        month = payload.get("month")

        # 여기서는 단순 로그만 남기지만, 필요 시 별도 Deadline 모델 저장 가능
        PartnerChangeLog.objects.create(
            user=request.user,
            action="set_deadline",
            detail=f"[{branch}] {month}월 기한 {deadline_day}일 설정"
        )
        return JsonResponse({"status": "success", "message": f"{branch} {month}월 기한 {deadline_day}일 설정 완료"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ============================================================
# 📘 5. 데이터 조회 (ajax_fetch)
# ============================================================

@grade_required(['superuser', 'main_admin', 'sub_admin'])
def ajax_fetch(request):
    """월도 기준으로 편제변경 데이터 조회"""
    month = request.GET.get("month")
    if not month:
        return JsonResponse({"rows": []})

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
            "request_date": obj.request_date.strftime("%Y-%m-%d"),
            "process_date": obj.process_date.strftime("%Y-%m-%d") if obj.process_date else "",
        })

    return JsonResponse({"rows": rows})