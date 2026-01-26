# django_ma/accounts/urls.py

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # ---------------------------------------------------------------------
    # Excel 업로드 진행률 polling
    #
    # 사용처:
    # - admin 사용자 엑셀 업로드 페이지
    # - task_id 기반으로 Celery 진행률/상태 조회
    #
    # GET /accounts/upload-progress/?task_id=...
    # ---------------------------------------------------------------------
    path(
        "upload-progress/",
        views.upload_progress_view,
        name="accounts_upload_progress",
    ),

    # ✅ 결과 파일 다운로드 (추가한 부분)
    path(
        "upload-result/<str:task_id>/",
        views.upload_result_view,
        name="accounts_upload_result",
    ),


    # ---------------------------------------------------------------------
    # User search API (SSOT)
    #
    # ✅ 권장 엔드포인트
    #   GET /accounts/api/search-user/
    #     ?q=키워드
    #     &scope=branch|...
    #     [&branch=지점명]
    #
    # - 공통 검색 모달
    # - manage-structure / manage-rate / support-form 등 공용
    # ---------------------------------------------------------------------
    path(
        "api/search-user/",
        views.api_search_user,
        name="api_search_user",
    ),

    # ---------------------------------------------------------------------
    # Legacy alias (하위 호환)
    #
    # ❌ 신규 개발에서는 사용 비권장
    # - 내부적으로는 api_search_user와 동일 동작
    # - 점진적 제거를 위해 유지
    #
    # GET /accounts/search-user/
    # ---------------------------------------------------------------------
    path(
        "search-user/",
        views.search_user,  # alias → api_search_user
        name="search_user_legacy",
    ),
]
