# django_ma/accounts/urls_api.py
from django.urls import path
from . import api_views

urlpatterns = [
    path("search-user/", api_views.search_user, name="search_user_api"),
]
