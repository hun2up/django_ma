from django.urls import path

from . import views

app_name = "commission"

urlpatterns = [
    # =========================================================================
    # Pages (UI)
    # =========================================================================
    path("", views.redirect_to_deposit, name="commission_home"),      # 기본 접속 → 채권관리로 이동
    path("deposit/", views.deposit_home, name="deposit_home"),       # 채권관리(채권현황)
    path("support/", views.support_home, name="support_home"),       # 지원신청서(페이지)
    path("approval/", views.approval_home, name="approval_home"),    # 수수료결재(페이지)

    # =========================================================================
    # Upload APIs
    # =========================================================================
    path("upload-excel/", views.upload_excel, name="upload_excel"),                  # 채권 데이터 업로드
    path("approval/upload-excel/", views.approval_upload_excel, name="approval_upload_excel"),  # 결재/효율 업로드

    # =========================================================================
    # Excel Download
    # =========================================================================
    path("approval/excel/pending/", views.download_approval_pending_excel, name="download_approval_pending_excel"),
    path("approval/excel/efficiency-excess/", views.download_efficiency_excess_excel, name="download_efficiency_excess_excel"),

    # =========================================================================
    # Data APIs (Deposit)
    # =========================================================================
    path("api/user-detail/", views.api_user_detail, name="api_user_detail"),
    path("api/deposit-summary/", views.api_deposit_summary, name="api_deposit_summary"),
    path("api/deposit-surety/", views.api_deposit_surety_list, name="api_deposit_surety_list"),
    path("api/deposit-other/", views.api_deposit_other_list, name="api_deposit_other_list"),
    path("api/support-pdf/", views.api_support_pdf, name="api_support_pdf"),
]
