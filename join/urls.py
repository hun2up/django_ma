# django_ma > join > urls.py
from django.urls import path
from . import views

app_name = 'join'

urlpatterns = [
    path('', views.redirect_to_manual, name='manual_basic'),
    path('success/', views.success_view, name='success'),
    path('dbtest/', views.db_test_view, name='db_test'),
    path('status/<str:task_id>/', views.task_status, name='task_status'),
    path('download/<str:task_id>/', views.download_pdf, name='download_pdf'),
    path('manual_basic/', views.manual_basic, name='manual_basic'),
    path('manual_head/', views.manual_head, name='manual_head'),
    path('rules_basic/', views.rules_head, name='rules_basic'),
    path('rules_head/', views.rules_head, name='rules_head'),
]
