# django_ma/commission/urls.py
from django.urls import path
from . import views

app_name = "commission"

urlpatterns = [
    path('', views.redirect_to_deposit, name='commission_home'),  # 기본 접속 시 채권관리로 이동
    path('deposit/', views.deposit_home, name='deposit_home'),    # 채권관리
    path('support/', views.support_home, name='support_home'),    # 지원신청서
    path('approval/', views.approval_home, name='approval_home'), # 수수료결재
    path('upload-excel/', views.upload_excel, name='upload_excel'), # ✅ 엑셀 업로드 API
    path("api/user-detail/", views.api_user_detail, name="api_user_detail"),
    path("api/deposit-summary/", views.api_deposit_summary, name="api_deposit_summary"),
    path("api/deposit-surety/", views.api_deposit_surety_list, name="api_deposit_surety_list"),
    path("api/deposit-other/", views.api_deposit_other_list, name="api_deposit_other_list"),
]
