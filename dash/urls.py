# django_ma/commission/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.redirect_to_sales, name='dash_home'),  # 기본 접속 시 매출 대시보드로 이동
    path('sales/', views.dash_sales, name='dash_sales'),  # 매출
    path('recruit/', views.dash_recruit, name='dash_recruit'), # 리쿠르팅
    path('retention/', views.dash_retention, name='dash_retention'), # 리쿠르팅
]
