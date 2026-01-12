from django.urls import path
from . import views

app_name = "manual"

urlpatterns = [
    # =========================================================
    # Pages
    # =========================================================
    path("", views.manual_list, name="manual_list"),
    path("<int:pk>/", views.manual_detail, name="manual_detail"),
    path("new/", views.manual_create, name="manual_create"),
    path("<int:pk>/edit/", views.manual_edit, name="manual_edit"),

    # =========================================================
    # Manual (AJAX)
    # =========================================================
    path("create-ajax/", views.manual_create_ajax, name="manual_create_ajax"),
    path("ajax/reorder/", views.manual_reorder_ajax, name="manual_reorder_ajax"),
    path("ajax/bulk-update/", views.manual_bulk_update_ajax, name="manual_bulk_update_ajax"),
    path("ajax/delete/", views.manual_delete_ajax, name="manual_delete_ajax"),
    path("ajax/title-update/", views.manual_update_title_ajax, name="manual_update_title_ajax"),

    # =========================================================
    # Section (AJAX)
    # =========================================================
    path("ajax/section-add/", views.manual_section_add_ajax, name="manual_section_add_ajax"),
    path("ajax/section-title/update/", views.manual_section_title_update_ajax, name="manual_section_title_update_ajax"),
    path("ajax/section/delete/", views.manual_section_delete_ajax, name="manual_section_delete_ajax"),
    path("ajax/section-reorder/", views.manual_section_reorder_ajax, name="manual_section_reorder_ajax"),

    # =========================================================
    # Block (AJAX)
    # =========================================================
    path("ajax/block-add/", views.manual_block_add_ajax, name="manual_block_add_ajax"),
    path("ajax/block-update/", views.manual_block_update_ajax, name="manual_block_update_ajax"),
    path("ajax/block/delete/", views.manual_block_delete_ajax, name="manual_block_delete_ajax"),
    path("ajax/block-reorder/", views.manual_block_reorder_ajax, name="manual_block_reorder_ajax"),

    # =========================================================
    # Block Attachments (AJAX)  ✅ NEW
    # =========================================================
    path("ajax/block-attachment/upload/", views.manual_block_attachment_upload_ajax, name="manual_block_attachment_upload_ajax"),
    path("ajax/block-attachment/delete/", views.manual_block_attachment_delete_ajax, name="manual_block_attachment_delete_ajax"),
]
