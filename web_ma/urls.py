"""
URL configuration for web_ma project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# django_ma > web_ma > urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from accounts.custom_admin import custom_admin_site
from home import views as home_views  # 메인 페이지 뷰
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from accounts.views import SessionCloseLoginView

def home_redirect(request):
    """홈(/) 접속 시 게시판으로 리다이렉트"""
    return redirect('post_list')

urlpatterns = [
    # ✅ 일반 사용자 로그아웃 (admin.site.logout 제거)
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    # ✅ 커스텀 관리자
    path('admin/', custom_admin_site.urls),
    path('', home_redirect, name='home'),
    path('login/', SessionCloseLoginView.as_view(template_name='registration/login.html'), name='login'),
    path('join/', include('join.urls')),
    path('board/', include('board.urls')),
    path('commission/', include('commission.urls')),
    path('dash/', include('dash.urls')),
    path('partner/', include('partner.urls')),
    path("api/accounts/", include("accounts.urls")),
    # path("ckeditor/", include("ckeditor_uploader.urls")),
]

# 개발 모드(DEBUG=True)에서만 업로드 파일 서빙
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)