# django_ma/accounts/urls.py
from django.urls import path
from . import views, api_views

app_name = "accounts"

urlpatterns = [
    # 진행률 조회
    path("upload-progress/", views.upload_progress_view, name="upload_progress"),

    # 공통 검색 API
    path("search-user/", api_views.search_user, name="search_user_api"),
]
