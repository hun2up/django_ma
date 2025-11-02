# django_ma/partner/urls.py
from django.urls import path
from . import views

app_name = "partner"

urlpatterns = [
    # ------------------------------------------------------------
    # 📘 메인 페이지
    # ------------------------------------------------------------
    path("", views.redirect_to_calculate, name="calculate_home"),
    path("calculate/", views.manage_calculate, name="manage_calculate"),
    path("grades/", views.manage_grades, name="manage_grades"),
    path("charts/", views.manage_charts, name="manage_charts"),
    path("rate/", views.manage_rate, name="manage_rate"),
    path("tables/", views.manage_tables, name="manage_tables"),
    path("upload-grades-excel/", views.upload_grades_excel, name="upload_grades_excel"),

    # ------------------------------------------------------------
    # 📘 공용 Ajax (편제·요율 공용)
    # ------------------------------------------------------------
    path("api/save/", views.ajax_save, name="ajax_save"),
    path("api/delete/", views.ajax_delete, name="ajax_delete"),
    path("api/fetch/", views.ajax_fetch, name="ajax_fetch"),
    path("api/update-process-date/", views.ajax_update_process_date, name="ajax_update_process_date"),

    # ------------------------------------------------------------
    # 📘 권한관리
    # ------------------------------------------------------------
    path("api/users-data/", views.ajax_users_data, name="ajax_users_data"),
    path("api/update-level/", views.ajax_update_level, name="ajax_update_level"),

    # ------------------------------------------------------------
    # 📘 공용 부서/지점 데이터
    # ------------------------------------------------------------
    path("ajax_fetch_parts/", views.ajax_fetch_parts, name="ajax_fetch_parts"),
    path("ajax_fetch_branches/", views.ajax_fetch_branches, name="ajax_fetch_branches"),

    # ------------------------------------------------------------
    # 📘 테이블 관리 (TableSetting)
    # ------------------------------------------------------------
    path("ajax_table_fetch/", views.ajax_table_fetch, name="ajax_table_fetch"),  # ✅ index.js와 일치
    path("ajax_table_save/", views.ajax_table_save, name="ajax_table_save"),

    # ------------------------------------------------------------
    # 📘 요율 관리 (RateTable)
    # ------------------------------------------------------------
    path("ajax/rate-userlist/", views.ajax_rate_userlist, name="ajax_rate_userlist"),
    path("ajax/rate-userlist-excel/", views.ajax_rate_userlist_excel, name="ajax_rate_userlist_excel"),
    path("ajax/rate-userlist-upload/", views.ajax_rate_userlist_upload, name="ajax_rate_userlist_upload"),
    path("ajax/rate-user-detail/", views.ajax_rate_user_detail, name="ajax_rate_user_detail"),
]