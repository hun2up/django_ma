# django_ma/board/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('create/', views.post_create, name='post_create'),  # 글 작성 페이지
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('support_form/', views.support_form, name='support_form'),
    path('support_manual/', views.support_manual, name='support_manual'),
    path('support_rules/', views.support_rules, name='support_rules'),
    path('support_form/', views.support_form, name='support_form'),
    path('search-user/', views.search_user, name='search_user'),
    path('generate-pdf/', views.generate_request_pdf, name='generate_pdf'),
]