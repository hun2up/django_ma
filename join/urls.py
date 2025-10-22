# django_ma > join > urls.py
from django.urls import path
from . import views

app_name = 'join'

urlpatterns = [
    path('', views.redirect_to_manual, name='support_manual'),
    path('success/', views.success_view, name='success'),
    path('dbtest/', views.db_test_view, name='db_test'),
    path('status/<str:task_id>/', views.task_status, name='task_status'),
    path('download/<str:task_id>/', views.download_pdf, name='download_pdf'),
    path('support_manual/', views.support_manual, name='support_manual'),
    path('support_rules/', views.support_rules, name='support_rules'),
]
