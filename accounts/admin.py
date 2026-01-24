# django_ma/accounts/admin.py
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Iterable, Optional

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path

from openpyxl import Workbook

from .constants import (
    CACHE_ERROR_PREFIX,
    CACHE_PROGRESS_PREFIX,
    CACHE_RESULT_PATH_PREFIX,
    CACHE_STATUS_PREFIX,
    CACHE_TIMEOUT_SECONDS,
    EXCEL_CONTENT_TYPE,
    cache_key,
)
from .custom_admin import custom_admin_site
from .forms import ExcelUploadForm
from .models import CustomUser
from .tasks import process_users_excel_task


TEMPLATE_REL_PATH = "accounts/excel/양식_계정관리.xlsx"
TEMPLATE_DOWNLOAD_NAME = "양식_계정관리.xlsx"

EXPORT_SELECTED_FILENAME = "selected_custom_users.xlsx"
EXPORT_ALL_FILENAME = "all_custom_users.xlsx"

DEFAULT_BATCH_SIZE = 500

SAFE_FILENAME_PATTERN = re.compile(r"[^0-9A-Za-z가-힣._-]+")

GRADE_DISPLAY = {
    "superuser": "Superuser",
    "main_admin": "Main Admin",
    "sub_admin": "Sub Admin",
    "basic": "Basic",
    "resign": "Resign",
    "inactive": "Inactive",
}


# -----------------------------------------------------------------------------
# Cache init (constants 기반)
# -----------------------------------------------------------------------------
def _init_upload_cache(task_id: str) -> None:
    cache.set(cache_key(CACHE_PROGRESS_PREFIX, task_id), 0, timeout=CACHE_TIMEOUT_SECONDS)
    cache.set(cache_key(CACHE_STATUS_PREFIX, task_id), "PENDING", timeout=CACHE_TIMEOUT_SECONDS)
    cache.delete(cache_key(CACHE_ERROR_PREFIX, task_id))
    cache.delete(cache_key(CACHE_RESULT_PATH_PREFIX, task_id))


# -----------------------------------------------------------------------------
# File helpers
# -----------------------------------------------------------------------------
def _get_upload_temp_dir() -> Path:
    media_root = Path(getattr(settings, "MEDIA_ROOT", "media"))
    default_dir = media_root / "upload_temp"
    temp_dir = Path(getattr(settings, "UPLOAD_TEMP_DIR", default_dir))
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _sanitize_filename(name: str, fallback: str = "upload.xlsx") -> str:
    raw = (name or "").strip() or fallback
    return SAFE_FILENAME_PATTERN.sub("_", raw)


def _save_uploaded_file_to_disk(uploaded_file, *, task_id: str) -> Path:
    temp_dir = _get_upload_temp_dir()
    safe_name = _sanitize_filename(getattr(uploaded_file, "name", "") or "upload.xlsx")
    save_path = temp_dir / f"accounts_upload_{task_id}_{safe_name}"

    with open(save_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    return save_path


def _file_response_or_404(abs_path: str | Path, *, download_name: Optional[str] = None) -> FileResponse:
    p = Path(abs_path)
    if not p.exists() or not p.is_file():
        raise Http404("파일을 찾을 수 없습니다.")
    fh = open(p, "rb")
    return FileResponse(fh, as_attachment=True, filename=(download_name or p.name))


# -----------------------------------------------------------------------------
# Excel export
# -----------------------------------------------------------------------------
def _build_users_export_workbook(users: Iterable[CustomUser]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = [
        "ID", "Name", "Branch", "Channel", "Division", "Part",
        "Grade", "Status", "입사일", "퇴사일", "Is Staff", "Is Active",
    ]
    ws.append(headers)

    for u in users:
        ws.append(
            [
                u.id,
                u.name,
                u.branch,
                u.channel,
                u.division,
                u.part,
                GRADE_DISPLAY.get(u.grade, u.grade),
                u.status,
                u.enter.strftime("%Y-%m-%d") if u.enter else "",
                u.quit.strftime("%Y-%m-%d") if u.quit else "",
                bool(u.is_staff),
                bool(u.is_active),
            ]
        )

    return wb


def export_users_as_excel(users: Iterable[CustomUser], filename: str) -> HttpResponse:
    wb = _build_users_export_workbook(users)
    response = HttpResponse(content_type=EXCEL_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def export_selected_users_to_excel(modeladmin, request, queryset):
    return export_users_as_excel(queryset, EXPORT_SELECTED_FILENAME)


def export_all_users_excel_view(request: HttpRequest) -> HttpResponse:
    return export_users_as_excel(CustomUser.objects.all(), EXPORT_ALL_FILENAME)


# -----------------------------------------------------------------------------
# Admin views
# -----------------------------------------------------------------------------
def upload_users_from_excel_view(request: HttpRequest) -> HttpResponse:
    template_name = "admin/accounts/customuser/upload_excel.html"
    incoming_task_id = (request.GET.get("task_id") or request.POST.get("task_id") or "").strip()

    if request.method != "POST":
        return render(request, template_name, {"form": ExcelUploadForm(), "task_id": incoming_task_id})

    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, template_name, {"form": form, "task_id": incoming_task_id, "error": "폼이 유효하지 않습니다."})

    excel_file = request.FILES.get("file")
    if not excel_file:
        return render(request, template_name, {"form": form, "task_id": incoming_task_id, "error": "파일이 첨부되지 않았습니다."})

    task_id = uuid.uuid4().hex

    try:
        save_path = _save_uploaded_file_to_disk(excel_file, task_id=task_id)
    except Exception as e:
        return render(request, template_name, {"form": ExcelUploadForm(), "task_id": incoming_task_id, "error": f"파일 저장 실패: {e}"})

    _init_upload_cache(task_id)

    # tasks.py에서도 동일 constants 사용하도록 아래에서 반영
    process_users_excel_task.delay(task_id, str(save_path), DEFAULT_BATCH_SIZE)

    return render(request, template_name, {"form": ExcelUploadForm(), "task_id": task_id, "message": "업로드 작업을 시작했습니다. 진행률을 확인하세요."})


def upload_users_result_view(request: HttpRequest, task_id: str) -> FileResponse:
    result_path = cache.get(cache_key(CACHE_RESULT_PATH_PREFIX, task_id))
    if not result_path:
        raise Http404("결과 파일을 찾을 수 없습니다.")
    return _file_response_or_404(result_path)


def upload_excel_template_view(request: HttpRequest) -> FileResponse:
    abs_path = finders.find(TEMPLATE_REL_PATH)
    if not abs_path:
        raise Http404("업로드 양식 파일을 찾을 수 없습니다.")

    p = Path(abs_path)
    if not p.exists():
        raise Http404("업로드 양식 파일을 찾을 수 없습니다.")

    fh = open(p, "rb")
    return FileResponse(
        fh,
        content_type=EXCEL_CONTENT_TYPE,
        as_attachment=True,
        filename=TEMPLATE_DOWNLOAD_NAME,
    )


@admin.register(CustomUser)
@admin.register(CustomUser, site=custom_admin_site)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    actions = [export_selected_users_to_excel]
    change_list_template = "admin/accounts/customuser/change_list.html"

    list_display = (
        "id", "name", "channel", "division", "part", "branch",
        "grade", "status", "enter", "quit",
        "is_staff", "is_active",
    )
    search_fields = ("id", "name", "channel", "division", "part", "branch", "grade", "status")
    ordering = ("id", "name", "channel", "division", "part", "branch")

    fieldsets = (
        (None, {"fields": ("id", "password")}),
        ("Personal Info", {"fields": ("name", "channel", "division", "part", "branch", "grade", "status", "enter", "quit")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    def save_model(self, request, obj, form, change):
        if obj.quit:
            obj.status = "퇴사"
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("export-all/", self.admin_site.admin_view(export_all_users_excel_view), name="export_all_users_excel"),
            path("upload-excel/", self.admin_site.admin_view(upload_users_from_excel_view), name="upload_users_excel"),
            path("upload-template/", self.admin_site.admin_view(upload_excel_template_view), name="upload_excel_template"),
            path("upload-result/<str:task_id>/", self.admin_site.admin_view(upload_users_result_view), name="upload_users_result"),
        ]
        return custom_urls + urls
