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
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

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
@login_required
@grade_required(["superuser", "main_admin", "sub_admin"])
def manage_charts(request):
    """편제변경 메인 페이지"""
    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"

    user = request.user
    user_branch = getattr(user, "branch", None)
    deadline_day = None
    selected_branch = None

    # 🔸 main_admin은 본인 branch 자동 설정
    if user.grade == "main_admin" and user_branch:
        selected_branch = user_branch
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
            f"{now.year}-{now.month + 1:02d}" if now.month < 12 else f"{now.year + 1}-01"
        ),
        "branches": BRANCH_PARTS,
        "deadline_day": deadline_day,
        "selected_branch": selected_branch,
        "data_fetch_url": "/partner/api/fetch/",
        "data_save_url": "/partner/api/save/",
        "data_delete_url": "/partner/api/delete/",
        "set_deadline_url": "/partner/api/set-deadline/",
        # 🆕 초기 데이터 표시 여부
        "auto_load": user.grade == "main_admin",  # main_admin만 true
    }
    return render(request, "partner/manage_charts.html", context)


# ------------------------------------------------------------
# 📘 2. 편제변경 — 데이터 저장 (완전 안정화 버전)
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

        # ✅ month 형식 보정 ("YYYY-M" → "YYYY-MM")
        if month:
            parts = month.split("-")
            if len(parts) == 2:
                y, m = parts
                month = f"{y}-{int(m):02d}"

        user = request.user
        part = payload.get("part") or getattr(user, "part", "") or "-"
        branch = payload.get("branch") or getattr(user, "branch", "") or "-"

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

        return JsonResponse({
            "status": "success",
            "saved_count": created_count,
            "message": f"{created_count}건 저장 완료"
        })

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
# 📘 5. 편제변경 — 데이터 조회 (sub_admin 새로고침 문제 완전 해결)
# ------------------------------------------------------------
@require_GET
@grade_required(["superuser", "main_admin", "sub_admin"])
def ajax_fetch(request):
    """AJAX — 편제변경 데이터 조회 (권한·레벨 기반 필터링 포함)"""
    try:
        # ✅ 월도 형식 보정
        month = (request.GET.get("month") or "").strip()
        if month:
            parts = month.split("-")
            if len(parts) == 2:
                y, m = parts
                month = f"{y}-{int(m):02d}"

        part = (request.GET.get("branch") or "").strip()
        user = request.user

        if not month:
            return JsonResponse({"status": "success", "rows": []})

        qs = StructureChange.objects.filter(month=month).select_related("requester", "target")

        # =======================================================
        # 🔐 권한별 데이터 접근 제한
        # =======================================================
        if user.grade == "superuser":
            # 전체 조회 가능
            if part:
                qs = qs.filter(branch=part)

        elif user.grade == "main_admin":
            # 본인 branch 내 데이터만
            qs = qs.filter(branch=user.branch)

        elif user.grade == "sub_admin":
            # ✅ SubAdminTemp 정보 조회
            sub_info = SubAdminTemp.objects.filter(user=user).first()

            if sub_info:
                level = (sub_info.level or "").strip()
                team_a = (sub_info.team_a or "").strip()
                team_b = (sub_info.team_b or "").strip()
                team_c = (sub_info.team_c or "").strip()

                # ------------------------------
                # 🟢 레벨별 필터링
                # ------------------------------
                if level == "A레벨" and team_a:
                    qs = qs.filter(requester__subadmin_detail__team_a=team_a)
                elif level == "B레벨" and team_b:
                    qs = qs.filter(requester__subadmin_detail__team_b=team_b)
                elif level == "C레벨" and team_c:
                    qs = qs.filter(requester__subadmin_detail__team_c=team_c)
                else:
                    # 레벨/팀 데이터 없으면 branch 기준으로 제한
                    qs = qs.filter(branch=user.branch)
            else:
                qs = qs.filter(branch=user.branch)

        # =======================================================
        # 🔧 유틸: 안전한 값 변환
        # =======================================================
        def safe(v):
            if isinstance(v, Decimal):
                return str(v)
            if hasattr(v, "strftime"):
                try:
                    return v.strftime("%Y-%m-%d")
                except Exception:
                    return str(v)
            return v or ""

        # =======================================================
        # 📦 데이터 직렬화
        # =======================================================
        rows = [
            {
                "id": sc.id,
                "requester_id": getattr(sc.requester, "id", ""),
                "requester_name": getattr(sc.requester, "name", ""),
                "branch": sc.branch or "",
                "target_id": getattr(sc.target, "id", ""),
                "target_name": getattr(sc.target, "name", ""),
                "target_branch": getattr(sc.target, "branch", ""),
                "chg_branch": safe(sc.chg_branch),
                "or_flag": bool(sc.or_flag),
                "rank": safe(sc.rank),
                "chg_rank": safe(sc.chg_rank),
                "memo": safe(sc.memo),
                "request_date": safe(sc.request_date),
                "process_date": safe(sc.process_date),
                "rate": safe(sc.rate),
                "chg_rate": safe(sc.chg_rate),
            }
            for sc in qs.order_by("-id")
        ]

        return JsonResponse({"status": "success", "rows": rows})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# ------------------------------------------------------------
# 📘 6. 권한관리 페이지 (조회 전용 버전)
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
# 📘 7. 권한관리 — 엑셀 업로드 처리 (조회 외 유일 수정 기능)
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
        return JsonResponse({"data": data, "recordsTotal": total_count, "recordsFiltered": total_count,}, safe=False)

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
# 📘 9. 레벨관리
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



