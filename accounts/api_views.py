# 📂 django_ma/accounts/api_views.py
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from partner.models import SubAdminTemp


@login_required
def search_user(request):
    """공통 사용자 검색 API — 권한 및 레벨 기반 검색 제한"""
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"results": []})

    user = request.user
    qs = CustomUser.objects.all()

    # =========================================
    # ✅ 1️⃣ superuser — 전체 검색 허용
    # =========================================
    if user.grade == "superuser":
        pass

    # =========================================
    # ✅ 2️⃣ main_admin — 동일 branch 내 전체 검색
    # =========================================
    elif user.grade == "main_admin":
        qs = qs.filter(branch=user.branch)

    # =========================================
    # ✅ 3️⃣ sub_admin — 레벨(A/B/C)에 따라 팀 단위 검색
    # =========================================
    elif user.grade == "sub_admin":
        sub_info = SubAdminTemp.objects.filter(user=user).first()

        if sub_info:
            level = (sub_info.level or "").strip()
            team_a = (sub_info.team_a or "").strip()
            team_b = (sub_info.team_b or "").strip()
            team_c = (sub_info.team_c or "").strip()

            if level == "A레벨" and team_a:
                qs = qs.filter(subadmin_detail__team_a=team_a)
            elif level == "B레벨" and team_b:
                qs = qs.filter(subadmin_detail__team_b=team_b)
            elif level == "C레벨" and team_c:
                qs = qs.filter(subadmin_detail__team_c=team_c)
            else:
                # 레벨이나 팀 정보가 없을 경우 branch로 제한
                qs = qs.filter(branch=user.branch)
        else:
            qs = qs.filter(branch=user.branch)

    # =========================================
    # ✅ 4️⃣ basic / inactive — 본인만 검색 가능
    # =========================================
    elif user.grade in ["basic", "inactive"]:
        qs = qs.filter(id=user.id)

    # =========================================
    # ✅ 5️⃣ 그 외 등급 — 검색 제한
    # =========================================
    else:
        return JsonResponse({"results": []})

    # =========================================
    # ✅ 검색 필터 적용 (성명, 사번, 지점명)
    # =========================================
    qs = qs.filter(
        Q(name__icontains=q) |
        Q(id__icontains=q) |
        Q(branch__icontains=q)
    )

    # =========================================
    # ✅ 결과 정리 및 반환
    # =========================================
    users = (
        qs.order_by("name")
        .values(
            "id", "name", "part", "branch", "regist",
            "enter", "quit", "grade", "status"
        )[:50]
    )

    return JsonResponse({"results": list(users)})
