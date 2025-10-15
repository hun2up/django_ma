# accounts/custom_admin.py
from django.contrib.admin import AdminSite
from django.shortcuts import render

class CustomAdminSite(AdminSite):
    site_header = "관리자 페이지"
    site_title = "관리자 포털"
    index_title = "Welcome to Admin Panel"

    def has_permission(self, request):
        """
        superuser grade만 접근 가능.
        """
        user = request.user
        if not user.is_authenticated or getattr(user, 'grade', None) != 'superuser':
            return False
        return True

    def login(self, request, extra_context=None):
        """
        로그인은 통과, 하지만 로그인 후 grade 확인에서 걸러짐.
        """
        if request.method == 'GET' and request.user.is_authenticated:
            if self.has_permission(request):
                return super().index(request)
            else:
                return render(request, 'no_permission_popup.html')  # ✅ 팝업 메시지 페이지
        return super().login(request, extra_context)

custom_admin_site = CustomAdminSite(name='custom_admin')