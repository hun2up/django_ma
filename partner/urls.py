# django_ma/partner/urls.py
from django.urls import path
from . import views

app_name = "partner"

urlpatterns = [
    # 📌 메인 페이지들
    path('', views.redirect_to_calculate, name='cacluate_home'), 
    path('calculate/', views.manage_calculate, name='manage_calculate'),  
    path('grades/', views.manage_grades, name='manage_grades'), 
    path("charts/", views.manage_charts, name="manage_charts"),
    path("rate/", views.manage_rate, name="manage_rate"),
    path("upload-grades-excel/", views.upload_grades_excel, name="upload_grades_excel"),

    # 📌 Ajax 엔드포인트
    path("api/save/", views.ajax_save, name="ajax_save"),
    path("api/delete/", views.ajax_delete, name="ajax_delete"),
    path("api/fetch/", views.ajax_fetch, name="ajax_fetch"),
    path("api/users-data/", views.ajax_users_data, name="ajax_users_data"),
    path("api/update-level/", views.ajax_update_level, name="ajax_update_level"),
]
