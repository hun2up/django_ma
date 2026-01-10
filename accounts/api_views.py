# django_ma/accounts/api_views.py
from __future__ import annotations

from django.http import JsonResponse, HttpRequest
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .models import CustomUser
from partner.models import SubAdminTemp


@login_required
def search_user(request: HttpRequest) -> JsonResponse:
    """
    공통 사용자 검색 API

    ✅ 핵심:
    - 기본 정책은 기존과 동일 (superuser 전체 / main_admin 지점 / sub_admin 팀 / basic 본인)
    - 단, manage_charts/manage_rate에서 쓰는 모달은 '지점단위 검색'이 필요하므로
      scope=branch 요청 시 sub_admin도 "본인 branch 전체" 검색 허용

    Query Params:
    - q: 검색어 (필수)
    - scope: "branch" | (기본값: "")
    - branch: (superuser일 때만 유효) 특정 지점 지정
    """
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})

    scope = (request.GET.get("scope") or "").strip().lower()
    requested_branch = (request.GET.get("branch") or "").strip()

    user = request.user
    qs = CustomUser.objects.all()

    # -------------------------------
    # 1) superuser
    # -------------------------------
    if user.grade == "superuser":
        # superuser는 branch 파라미터가 오면 해당 지점으로 제한 가능
        if scope == "branch" and requested_branch:
            qs = qs.filter(branch=requested_branch)

    # -------------------------------
    # 2) main_admin
    # -------------------------------
    elif user.grade == "main_admin":
        # main_admin은 무조건 본인 지점
        qs = qs.filter(branch=user.branch)

    # -------------------------------
    # 3) sub_admin
    # -------------------------------
    elif user.grade == "sub_admin":
        # ✅ scope=branch면 "본인 branch 전체" 허용 (요청하신 개선 포인트)
        if scope == "branch":
            qs = qs.filter(branch=user.branch)
        else:
            # 기본은 기존처럼 "레벨/팀 단위" 제한
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
                    qs = qs.filter(branch=user.branch)
            else:
                qs = qs.filter(branch=user.branch)

    # -------------------------------
    # 4) basic / inactive
    # -------------------------------
    elif user.grade in ["basic", "inactive"]:
        qs = qs.filter(id=user.id)

    # -------------------------------
    # 5) 기타 등급
    # -------------------------------
    else:
        return JsonResponse({"results": []})

    # -------------------------------
    # 검색어 필터
    # -------------------------------
    qs = qs.filter(
        Q(name__icontains=q) |
        Q(id__icontains=q) |
        Q(branch__icontains=q)
    )

    users = (
        qs.order_by("name")
        .values(
            "id", "name", "part", "branch", "regist",
            "enter", "quit", "grade", "status"
        )[:50]
    )

    return JsonResponse({"results": list(users)})
