# django_ma/manual/templates/manual/urls.py

from django.urls import path
from . import views

app_name = "manual"

urlpatterns = [
    path("", views.manual_list, name="manual_list"),
    path("create-ajax/", views.manual_create_ajax, name="manual_create_ajax"),
    path("new/", views.manual_create, name="manual_create"),
    path("<int:pk>/", views.manual_detail, name="manual_detail"),   
    path("<int:pk>/edit/", views.manual_edit, name="manual_edit"),
    path("ajax/reorder/", views.manual_reorder_ajax, name="manual_reorder_ajax"),
    path("ajax/delete/", views.manual_delete_ajax, name="manual_delete_ajax"),
]
