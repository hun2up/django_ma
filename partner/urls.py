# django_ma/partner/urls.py

from django.urls import path
from . import views

app_name = "partner"

urlpatterns = [
    # ------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------
    path("", views.redirect_to_calculate, name="calculate_home"),
    path("calculate/", views.manage_calculate, name="manage_calculate"),
    path("grades/", views.manage_grades, name="manage_grades"),
    path("charts/", views.manage_charts, name="manage_charts"),
    path("rate/", views.manage_rate, name="manage_rate"),
    path("tables/", views.manage_tables, name="manage_tables"),
    path("upload-grades-excel/", views.upload_grades_excel, name="upload_grades_excel"),
    path("efficiency/upload-confirm/", views.efficiency_confirm_upload, name="efficiency_confirm_upload"),

    # ------------------------------------------------------------
    # Structure Change (편제변경) - 전용 API
    # ------------------------------------------------------------
    path("api/structure/fetch/", views.structure_fetch, name="structure_fetch"),
    path("api/structure/save/", views.structure_save, name="structure_save"),
    path("api/structure/delete/", views.structure_delete, name="structure_delete"),
    path(
        "api/structure/update-process-date/",
        views.ajax_update_process_date,
        name="structure_update_process_date",
    ),

    # ------------------------------------------------------------
    # Rate Change (요율변경) - 전용 API
    # ------------------------------------------------------------
    path("api/rate/fetch/", views.rate_fetch, name="rate_fetch"),
    path("api/rate/save/", views.rate_save, name="rate_save"),
    path("api/rate/delete/", views.rate_delete, name="rate_delete"),

    # ✅ 요율 처리일자 전용 alias (view는 공용 재사용)
    path(
        "api/rate/update-process-date/",
        views.ajax_update_process_date,
        name="rate_update_process_date",
    ),

    # ------------------------------------------------------------
    # Efficiency (지점효율) - 전용 API (추가)
    # ------------------------------------------------------------
    path("api/efficiency/fetch/", views.efficiency_fetch, name="efficiency_fetch"),
    path("api/efficiency/save/", views.efficiency_save, name="efficiency_save"),
    path("api/efficiency/delete/", views.efficiency_delete, name="efficiency_delete"),
    # (선택) 처리일자 alias를 따로 두고 싶으면
    path("api/efficiency/update-process-date/", views.ajax_update_process_date, name="efficiency_update_process_date"),

    # ------------------------------------------------------------
    # Permission Management
    # ------------------------------------------------------------
    path("api/users-data/", views.ajax_users_data, name="ajax_users_data"),
    path("api/update-level/", views.ajax_update_level, name="ajax_update_level"),

    # ------------------------------------------------------------
    # Part/Branch utilities
    # ------------------------------------------------------------
    path("ajax/fetch-parts/", views.ajax_fetch_parts, name="ajax_fetch_parts"),
    path("ajax/fetch-branches/", views.ajax_fetch_branches, name="ajax_fetch_branches"),

    # ------------------------------------------------------------
    # Table Setting
    # ------------------------------------------------------------
    path("ajax/table-fetch/", views.ajax_table_fetch, name="ajax_table_fetch"),
    path("ajax/table-save/", views.ajax_table_save, name="ajax_table_save"),

    # ------------------------------------------------------------
    # RateTable (요율현황)
    # ------------------------------------------------------------
    path("ajax/rate-userlist/", views.ajax_rate_userlist, name="ajax_rate_userlist"),
    path("ajax/rate-userlist-excel/", views.ajax_rate_userlist_excel, name="ajax_rate_userlist_excel"),
    path("ajax/rate-userlist-upload/", views.ajax_rate_userlist_upload, name="ajax_rate_userlist_upload"),
    path("ajax/rate-user-detail/", views.ajax_rate_user_detail, name="ajax_rate_user_detail"),

    # ------------------------------------------------------------
    # Legacy aliases (편제 공용)
    # ------------------------------------------------------------
    path("api/fetch/", views.structure_fetch, name="ajax_fetch"),
    path("api/save/", views.structure_save, name="ajax_save"),
    path("api/delete/", views.structure_delete, name="ajax_delete"),
    path("api/update-process-date/", views.ajax_update_process_date, name="ajax_update_process_date"),

    path("ajax/rate-userlist-template-excel/", views.ajax_rate_userlist_template_excel, name="ajax_rate_userlist_template_excel"),    
]
