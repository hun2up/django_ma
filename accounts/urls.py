# django_ma/accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("upload-progress/", views.upload_progress_view, name="accounts_upload_progress"),

    # ✅ (호환) 예전 경로도 같은 뷰로 처리
    path("search-user/", views.search_user, name="search_user_api"),

    # ✅ (권장) 공통 모달에서 쓰는 경로
    path("api/accounts/search-user/", views.api_search_user, name="api_search_user"),
]
