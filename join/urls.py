# join/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.join_form, name='join_form'),  # /join/
]
