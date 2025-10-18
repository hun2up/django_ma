# django_ma/accounts/custom_admin.py
from django.contrib.admin import AdminSite
from django.shortcuts import render

class CustomAdminSite(AdminSite):
    site_header = "관리자 페이지"
    site_title = "관리자 포털"
    index_title = "MA 업무지원 사이트 관리자 페이지 입니다."

    def has_permission(self, request):
        user = request.user
        return user.is_authenticated and getattr(user, 'grade', '') == 'superuser'

    def login(self, request, extra_context=None):
        if request.method == 'GET' and request.user.is_authenticated:
            if self.has_permission(request):
                return super().index(request)
            else:
                return render(request, 'no_permission_popup.html')
        return super().login(request, extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')
