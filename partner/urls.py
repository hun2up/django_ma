# django_ma/commission/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.redirect_to_calculate, name='cacluate_home'),  # 기본 접속 시 매출 대시보드로 이동
    path('calculate/', views.manage_calculate, name='manage_calculate'),  # 매출
    path('charts/', views.manage_charts, name='manage_charts'), # 리쿠르팅
    path('grades/', views.manage_grades, name='manage_grades'), # 리쿠르팅
]
