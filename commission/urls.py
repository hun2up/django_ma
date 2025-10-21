# django_ma/commission/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.redirect_to_deposit, name='commission_home'),  # 기본 접속 시 채권관리로 이동
    path('deposit/', views.deposit_home, name='deposit_home'),    # 채권관리
    path('support/', views.support_home, name='support_home'),    # 지원신청서
    path('approval/', views.approval_home, name='approval_home'), # 수수료결재
    path('search-user/', views.search_user, name='search_user'), # ✅ 대상자 검색 API
    path('upload-excel/', views.upload_excel, name='upload_excel'), # ✅ 엑셀 업로드 API
]
