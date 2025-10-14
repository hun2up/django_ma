from django.urls import path
from . import views

app_name = 'join'  # ✅ 추가: URL 이름에 네임스페이스 붙이기

urlpatterns = [
    path('', views.join_form, name='form'),                # ✅ name 변경
    path('success/', views.success_view, name='success'),  # ✅ success 페이지 추가
    path('dbtest/', views.db_test_view, name='db_test'),
    path('status/<str:task_id>/', views.task_status, name='task_status'),
    path('download/<str:task_id>/', views.download_pdf, name='download_pdf'),
]
