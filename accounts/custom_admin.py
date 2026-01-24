# django_ma/accounts/custom_admin.py
from __future__ import annotations

from django.contrib.admin import AdminSite
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render


class CustomAdminSite(AdminSite):
    site_header = "관리자 페이지"
    site_title = "관리자 포털"
    index_title = "MA 업무지원 사이트 관리자 페이지 입니다."

    def has_permission(self, request) -> bool:
        user = request.user
        return bool(user.is_authenticated and getattr(user, "grade", "") == "superuser")

    def login(self, request, extra_context=None):
        """
        이미 로그인된 사용자가 /admin/login/ 로 접근했을 때:
        - superuser grade면 index로 이동(관리자 메인)
        - 아니면 no_permission_popup 표시
        """
        if request.method == "GET" and request.user.is_authenticated:
            if self.has_permission(request):
                return super().index(request)
            return render(request, "no_permission_popup.html")

        return super().login(request, extra_context=extra_context)

    def logout(self, request, extra_context=None):
        """
        관리자 로그아웃 시 루트(/)로 이동
        """
        auth_logout(request)
        return redirect("/")


custom_admin_site = CustomAdminSite(name="custom_admin")
