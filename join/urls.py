# django_ma/join/urls.py
from django.urls import path
from . import views

app_name = "join"

urlpatterns = [
    # 기본 진입
    path("", views.redirect_to_manual, name="join_basic"),

    # 매뉴얼(일반/관리자)
    path("manual_basic/", views.manual_basic, name="manual_basic"),
    path("manual_head/", views.manual_head, name="manual_head"),

    # 영업기준안(일반/관리자)
    path("rules_basic/", views.rules_basic, name="rules_basic"),
    path("rules_head/", views.rules_head, name="rules_head"),

    # (선택) 매뉴얼 게시형 CRUD
    path("manual/", views.manual_list, name="manual_list"),
    path("manual/<int:pk>/", views.manual_detail, name="manual_detail"),
    path("manual/new/", views.manual_create, name="manual_create"),
    path("manual/<int:pk>/edit/", views.manual_edit, name="manual_edit"),

    # 위촉서류(PDF)
    path("form/", views.join_form, name="join_form"),
    path("task-status/<str:task_id>/", views.task_status, name="task_status"),
    path("download/<str:task_id>/", views.download_pdf, name="download_pdf"),
    path("success/", views.success_view, name="success"),
]
