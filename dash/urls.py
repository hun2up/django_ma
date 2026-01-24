# django_ma/dash/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.redirect_to_sales, name='dash_home'),
    path('sales/', views.dash_sales, name='dash_sales'),
    path('sales/upload/', views.upload_sales_excel, name='dash_sales_upload'),
    path('recruit/', views.dash_recruit, name='dash_recruit'),
    path('retention/', views.dash_retention, name='dash_retention'),
    path('goals/', views.dash_goals, name='dash_goals'),
]
