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
    path("ajax/update-post-field/", views.ajax_update_post_field, name="ajax_update_post_field"),
    path("ajax/post/<int:pk>/update-field/", views.ajax_update_post_field_detail, name="ajax_update_post_field_detail"),

    # ✅ 직원업무(task) - 신규
    path("task/", views.task_list, name="task_list"),
    path("task/create/", views.task_create, name="task_create"),
    path("task/<int:pk>/", views.task_detail, name="task_detail"),
    path("task/<int:pk>/edit/", views.task_edit, name="task_edit"),
    path("task/ajax/update-task-field/", views.ajax_update_task_field, name="ajax_update_task_field"),
    path("task/ajax/task/<int:pk>/update-field/", views.ajax_update_task_field_detail, name="ajax_update_task_field_detail"),
]