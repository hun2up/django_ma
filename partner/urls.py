# django_ma/commission/urls.py
from django.urls import path
from . import views

app_name = "partner"

urlpatterns = [
    path('', views.redirect_to_calculate, name='cacluate_home'),
    path('calculate/', views.manage_calculate, name='manage_calculate'),
    path('grades/', views.manage_grades, name='manage_grades'),
    path("grades/upload/", views.upload_grades_excel, name="upload_grades_excel"),
    path("charts/", views.manage_charts, name="manage_charts"),
    path("rate/", views.manage_charts, name="manage_rate"),
    path("api/save/", views.ajax_save, name="ajax_save"),
    path("api/delete/", views.ajax_delete, name="ajax_delete"),
    path("api/set-deadline/", views.ajax_set_deadline, name="ajax_set_deadline"),
    path("api/fetch/", views.ajax_fetch, name="ajax_fetch"),
]
