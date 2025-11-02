# django_ma/partner/views.py
import json
import traceback
from datetime import datetime
from decimal import Decimal
import pandas as pd

from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .models import StructureChange, PartnerChangeLog, StructureDeadline, SubAdminTemp, TableSetting


# ------------------------------------------------------------
# 공용 상수
# ------------------------------------------------------------
BRANCH_PARTS = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]


# ------------------------------------------------------------
# 📘 기본 페이지 리디렉션
# ------------------------------------------------------------
@login_required
def redirect_to_calculate(request):
    """기본 수수료 페이지 접속 시 → 채권관리 페이지로 리다이렉트"""
    return redirect("partner:manage_calculate")


@login_required
@grade_required(['superuser', 'main_admin', 'sub_admin'])
def manage_calculate(request):
    """지점효율 (제작중)"""
    return render(request, "partner/manage_calculate.html")


# ------------------------------------------------------------
# 📘 요율변경 요청 페이지
# ------------------------------------------------------------
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_rate(request):
    """요율변경 요청 페이지"""
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    context = {
        "current_year": current_year,
        "current_month": current_month,
        "selected_year": current_year,
        "selected_month": current_month,
        "auto_load": True,  # sub_admin 자동조회
        # ✅ JS가 참조할 URL들
        "data_fetch_url": "/partner/api/fetch/",
        "data_save_url": "/partner/api/save/",
        "data_delete_url": "/partner/api/delete/",
    }
    return render(request, "partner/manage_rate.html", context)


# ------------------------------------------------------------
# 📘 테이블 관리 페이지
# ------------------------------------------------------------
@login_required
@grade_required(['superuser', 'main_admin'])
def manage_tables(request):
    """테이블관리 (제작중)"""
    return render(request, "partner/manage_tables.html")


# ------------------------------------------------------------
# 📘 편제변경 메인 페이지
# ------------------------------------------------------------
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_charts(request):
    """편제변경 메인 페이지"""
    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"
    user = request.user

    selected_branch = None
    subadmin_info = SubAdminTemp.objects.filter(user=user).first()
    if user.grade == "main_admin" and user.branch:
        selected_branch = user.branch

    context = {
        "current_year": now.year,
        "current_month": now.month,
        "selected_year": now.year,
        "selected_month": now.month,
        "available_periods": [f"{now.year}-{m:02d}" for m in range(1, now.month + 1)],
        "future_select_until": (
            f"{now.year}-{now.month + 1:02d}" if now.month < 12 else f"{now.year + 1}-01"
        ),
        "branches": BRANCH_PARTS,
        "selected_branch": selected_branch,
        "data_fetch_url": "/partner/api/fetch/",
        "data_save_url": "/partner/api/save/",
        "data_delete_url": "/partner/api/delete/",
        "set_deadline_url": "/partner/api/set-deadline/",
        "auto_load": user.grade in ["main_admin", "sub_admin"],
        "subadmin_info": subadmin_info,
    }
    return render(request, "partner/manage_charts.html", context)


# ------------------------------------------------------------
# 📘 AJAX — 데이터 저장 (공용)
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_save(request):
    """AJAX — 대상자 입력내용 저장"""
    try:
        payload = json.loads(request.body)
        items = payload.get("rows", [])
        month = (payload.get("month") or "").strip()
        if month and "-" in month:
            y, m = month.split("-")
            month = f"{y}-{int(m):02d}"

        user = request.user
        part = payload.get("part") or getattr(user, "part", "") or "-"
        branch = payload.get("branch") or getattr(user, "branch", "") or "-"
        if user.grade in ["main_admin", "sub_admin"]:
            branch = getattr(user, "branch", "") or branch

        created_count = 0
        for row in items:
            target = CustomUser.objects.filter(id=row.get("target_id")).first()
            if not target:
                continue
            StructureChange.objects.create(
                requester=user,
                target=target,
                part=part,
                branch=branch,
                target_branch=getattr(target, "branch", "") or "-",
                chg_branch=row.get("chg_branch") or "-",
                or_flag=row.get("or_flag", False),
                rank=row.get("tg_rank") or "-",
                chg_rank=row.get("chg_rank") or "-",
                memo=row.get("memo") or "",
                month=month,
            )
            created_count += 1

        PartnerChangeLog.objects.create(
            user=user,
            action="save",
            detail=f"{created_count}건 저장 (월도: {month}, 부서: {part}, 지점: {branch})",
        )

        return JsonResponse({"status": "success", "saved_count": created_count})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 AJAX — 데이터 삭제
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin", "sub_admin"])
@transaction.atomic
def ajax_delete(request):
    """AJAX — 편제변경/요율변경 행 삭제"""
    try:
        data = json.loads(request.body or "{}")
        record_id = data.get("id")
        if not record_id:
            return JsonResponse({"status": "error", "message": "id 누락"}, status=400)

        record = get_object_or_404(StructureChange, id=record_id)
        user = request.user
        if not (
            user.grade in ["superuser", "main_admin"] or record.requester_id == user.id
        ):
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


# ------------------------------------------------------------
# 📘 AJAX — 데이터 조회 (fetch)
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_fetch(request):
    """AJAX — 편제변경/요율변경 데이터 조회"""
    try:
        user = request.user
        month = (request.GET.get("month") or "").strip()
        branch = (request.GET.get("branch") or "").strip()

        if month and "-" in month:
            y, m = month.split("-")
            month = f"{y}-{int(m):02d}"

        qs = StructureChange.objects.filter(month=month).select_related("requester", "target")
        if user.grade == "superuser" and branch:
            qs = qs.filter(branch__iexact=branch)
        elif user.grade == "main_admin":
            qs = qs.filter(branch__iexact=user.branch)
        elif user.grade == "sub_admin":
            qs = qs.filter(branch__iexact=user.branch)

        rows = [
            {
                "id": sc.id,
                "requester_id": getattr(sc.requester, "id", ""),
                "requester_name": getattr(sc.requester, "name", ""),
                "requester_branch": getattr(sc.requester, "branch", ""),
                "target_id": getattr(sc.target, "id", ""),
                "target_name": getattr(sc.target, "name", ""),
                "table_before": getattr(sc, "branch", ""),
                "table_after": getattr(sc, "chg_branch", ""),
                "rate_before": getattr(sc, "rank", ""),
                "rate_after": getattr(sc, "chg_rank", ""),
                "memo": sc.memo or "",
                "process_date": sc.process_date.strftime("%Y-%m-%d") if sc.process_date else "",
            }
            for sc in qs
        ]
        return JsonResponse({"status": "success", "rows": rows})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e), "rows": []}, status=500)


# ------------------------------------------------------------
# 주요 코드 구분 주석
# ------------------------------------------------------------


# ------------------------------------------------------------
# 📘 4. 편제변경 — 처리일자 수정
# ------------------------------------------------------------
@require_POST
@grade_required(["superuser", "main_admin"])
@transaction.atomic
def ajax_update_process_date(request):
    """AJAX — 메인시트 처리일자 수정"""
    try:
        payload = json.loads(request.body)
        record_id = payload.get("id")
        new_date = payload.get("process_date")

        record = get_object_or_404(StructureChange, id=record_id)

        # YYYY-MM-DD 형식 검증
        try:
            parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"status": "error", "message": "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)"}, status=400)

        record.process_date = parsed_date
        record.save(update_fields=["process_date"])

        PartnerChangeLog.objects.create(
            user=request.user,
            action="update_process_date",
            detail=f"ID {record_id} 처리일자 수정 → {new_date}",
        )

        return JsonResponse({"status": "success", "message": f"처리일자 {new_date}로 변경 완료"})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 권한관리 페이지 (조회 전용 버전)
# ------------------------------------------------------------
# partner/views.py
@login_required
@grade_required(["superuser", "main_admin"])
def manage_grades(request):
    """권한관리 페이지"""
    user = request.user
    selected_part = request.GET.get("part", "").strip() or None
    parts = ["MA사업1부", "MA사업2부", "MA사업3부", "MA사업4부"]

    base_user_qs = CustomUser.objects.filter(grade="sub_admin")
    
    # ✅ 중간관리자(SubAdminTemp)
    if user.grade == "superuser":
        if selected_part:
            subadmin_qs = SubAdminTemp.objects.filter(part=selected_part, user__in=base_user_qs)
        else:
            subadmin_qs = SubAdminTemp.objects.none()  # 선택 전엔 빈 상태
    elif user.grade == "main_admin":
        selected_part = user.branch
        subadmin_qs = SubAdminTemp.objects.filter(branch=user.branch, user__in=base_user_qs)
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

    LEVELS = ["-", "A레벨", "B레벨", "C레벨"]

    return render(request, "partner/manage_grades.html", {
        "parts": parts,
        "selected_part": selected_part,
        "users_subadmin": subadmin_qs,
        "users_all": users_all,
        "empty_message_subadmin": empty_message_subadmin,
        "levels": LEVELS,
    })


# ------------------------------------------------------------
# 📘 권한관리 — 엑셀 업로드 처리 (조회 외 유일 수정 기능)
# ------------------------------------------------------------
@transaction.atomic
@login_required
def upload_grades_excel(request):
    """
    ✅ 엑셀 업로드를 통한 전체설계사 명단(allUserTable) 갱신
    - SubAdminTemp(=allUserTable 저장소)에만 반영
    - CustomUser는 수정하지 않음
    - 이후 중간관리자(subAdminTable)는 CustomUser.grade=sub_admin 필터로 SubAdminTemp와 매칭
    """
    if request.method == "POST" and request.FILES.get("excel_file"):
        file = request.FILES["excel_file"]

        try:
            # 📘 '업로드' 시트에서 읽기
            df = pd.read_excel(file, sheet_name="업로드").fillna("")

            required_cols = ["사번", "팀A", "팀B", "팀C", "직급"]
            for col in required_cols:
                if col not in df.columns:
                    messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                    return redirect("partner:manage_grades")

            # ✅ 부서/지점/등급은 무시
            ignore_cols = ["부서", "지점", "등급"]
            for col in ignore_cols:
                if col in df.columns:
                    df = df.drop(columns=[col])

            updated, created = 0, 0

            for _, row in df.iterrows():
                user_id = str(row["사번"]).strip()
                cu = CustomUser.objects.filter(id=user_id).first()
                if not cu:
                    continue  # 존재하지 않는 사번은 스킵

                # ✅ 전체사용자(allUserTable = SubAdminTemp)에 업데이트
                obj, is_created = SubAdminTemp.objects.update_or_create(
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
            import traceback
            traceback.print_exc()
            messages.error(request, f"엑셀 처리 중 오류 발생: {e}")

    else:
        messages.warning(request, "엑셀 파일을 선택하세요.")

    return redirect("partner:manage_grades")


# ------------------------------------------------------------
# 📘 권한관리 — 전체 사용자 Ajax 조회 (조회 전용)
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
        return JsonResponse({
            "data": [],
            "recordsTotal": 0,
            "recordsFiltered": 0
    })

    # ✅ 검색 조건 추가 (팀A/B/C까지 포함)
    if search:
        # 먼저 CustomUser 기준 필터링
        user_ids_from_custom = list(
            qs.filter(
                Q(name__icontains=search)
                | Q(id__icontains=search)
                | Q(branch__icontains=search)
                | Q(part__icontains=search)
            ).values_list("id", flat=True)
        )

        # 그 다음 SubAdminTemp(팀/직급)에서 검색되는 user_id 추출
        user_ids_from_subadmin = list(
            SubAdminTemp.objects.filter(
                Q(team_a__icontains=search)
                | Q(team_b__icontains=search)
                | Q(team_c__icontains=search)
                | Q(position__icontains=search)
            ).values_list("user_id", flat=True)
        )

        # 두 결과를 합쳐서 중복 제거
        combined_user_ids = set(user_ids_from_custom + user_ids_from_subadmin)

        qs = qs.filter(id__in=combined_user_ids)

    # ✅ 페이징 처리
    total_count = qs.count()
    paginator = Paginator(qs.only("id", "name", "branch", "part", "grade")[:2000], length)
    page_number = start // length + 1
    page = paginator.get_page(page_number)

    # ✅ SubAdminTemp 매핑 (팀A/B/C/직급 정보 포함)
    subadmin_map = {
        str(sa.user_id): {
            "position": sa.position or "",
            "team_a": sa.team_a or "",
            "team_b": sa.team_b or "",
            "team_c": sa.team_c or "",
        }
        for sa in SubAdminTemp.objects.filter(user_id__in=[u.id for u in page])
    }

    # ✅ DataTables JSON 변환
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



# ------------------------------------------------------------
# 📘 레벨관리
# ------------------------------------------------------------
@require_POST
@csrf_exempt  # ⚠️ 필요 시만 (ajax 요청시 CSRF 토큰 안 보낼 경우)
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


# ------------------------------------------------------------
# 📘 부서 목록 불러오기
# ------------------------------------------------------------
@login_required
@grade_required(['superuser'])
def ajax_fetch_parts(request):
    """
    등록된 모든 부서(part) 목록 반환
    """

    # 제외할 부서명 리스트 (정확히 일치)
    exclude_list = ["1인GA사업부", "MA사업0부"]

    parts = (
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
        .exclude(part__in=exclude_list)  # 🚫 특정 부서 제외
        .values_list("part", flat=True)
        .distinct()
        .order_by("part")
    )
    return JsonResponse({"parts": list(parts)})


# ------------------------------------------------------------
# 📘 지점 목록 불러오기
# ------------------------------------------------------------
@login_required
@grade_required(['superuser'])
def ajax_fetch_branches(request):
    """
    선택된 부서(part)에 해당하는 모든 지점(branch) 목록 반환
    """
    part = request.GET.get("part")
    if not part:
        return JsonResponse({"branches": []})

    # part와 정확히 일치하는 사용자만 필터링 (공백/NULL 제거)
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
# 📘 AJAX — 테이블관리 데이터 조회
# ------------------------------------------------------------
@require_GET
@login_required
@grade_required(['superuser', 'main_admin', 'sub_admin'])
def ajax_table_fetch(request):
    """
    ✅ 지점(branch)별 테이블 관리 데이터 조회
    - superuser는 모든 지점 조회 가능
    - main_admin, sub_admin, basic은 자신의 지점만 조회 가능
    - order 순서대로 정렬하여 반환
    """

    branch = request.GET.get("branch", "").strip()
    user = request.user

    # 🔹 branch 검증
    if not branch:
        return JsonResponse({"status": "error", "message": "지점(branch) 정보가 없습니다."})

    # 🔹 권한별 branch 접근 제한
    if user.grade != "superuser" and branch != user.branch:
        return JsonResponse({"status": "error", "message": "다른 지점의 테이블에는 접근할 수 없습니다."})

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
        import traceback
        print("❌ ajax_table_fetch 오류:", traceback.format_exc())
        return JsonResponse({"status": "error", "message": f"조회 중 오류 발생: {str(e)}"})


# ------------------------------------------------------------
# 📘 AJAX — 테이블관리 데이터 저장
# ------------------------------------------------------------
@require_POST
@login_required
@grade_required(['superuser', 'main_admin'])
def ajax_table_save(request):
    """
    테이블 관리 데이터 저장
    - branch별 기존 데이터 전체 삭제 후 재삽입
    - order(순서) 필드 포함 저장
    """
    import json
    from django.db import transaction
    from django.http import JsonResponse
    from .models import TableSetting

    try:
        data = json.loads(request.body.decode("utf-8"))
        branch = data.get("branch")
        rows = data.get("rows", [])

        if not branch or not isinstance(rows, list):
            return JsonResponse({"status": "error", "message": "요청 데이터가 잘못되었습니다."})

        with transaction.atomic():
            # 기존 branch 데이터 전체 삭제
            TableSetting.objects.filter(branch=branch).delete()

            # 새 데이터 삽입
            objs = []
            for r in rows:
                order = int(r.get("order") or 0)
                table_name = (r.get("table") or "").strip()
                rate = (r.get("rate") or "").strip()
                if not table_name and not rate:
                    continue

                objs.append(TableSetting(
                    branch=branch,
                    table_name=table_name,
                    rate=rate,
                    order=order,
                ))

            TableSetting.objects.bulk_create(objs)

        return JsonResponse({"status": "success", "saved_count": len(objs)})

    except Exception as e:
        import traceback
        print("❌ ajax_table_save 오류:", traceback.format_exc())
        return JsonResponse({"status": "error", "message": str(e)})
