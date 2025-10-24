# django_ma/board/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('create/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('support_form/', views.support_form, name='support_form'),
    path('states_form/', views.states_form, name='states_form'),
    path('search-user/', views.search_user, name='search_user'),
    path('generate-support/', views.generate_request_support, name='generate_request_support'),
    path('generate-states/', views.generate_request_states, name='generate_request_states'),
]