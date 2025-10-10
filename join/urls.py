# join/urls.py
from django.urls import path
from . import views
from .views import db_test_view

urlpatterns = [
    path('', views.join_form, name='join_form'),
    path('dbtest/', db_test_view, name='db_test'),  # /join/
]

