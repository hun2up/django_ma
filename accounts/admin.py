# django_ma/accounts/admin.py

# =============================================================================
# 📂 관리자 페이지 설정 — CustomUser Excel Import / Export
# =============================================================================
from __future__ import annotations

import os
import uuid
import re
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import render
from django.urls import path, reverse

from openpyxl import Workbook

from .forms import ExcelUploadForm
from .models import CustomUser
from .custom_admin import custom_admin_site
from .tasks import process_users_excel_task


# =============================================================================
# 0) 상수
# =============================================================================
EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

TEMPLATE_REL_PATH = "accounts/excel/양식_계정관리.xlsx"
TEMPLATE_DOWNLOAD_NAME = "양식_계정관리.xlsx"

GRADE_DISPLAY = {
    "superuser": "Superuser",
    "main_admin": "Main Admin",
    "sub_admin": "Sub Admin",
    "basic": "Basic",
    "resign": "Resign",
    "inactive": "Inactive",
}


# =============================================================================
# 1) Export helpers
# =============================================================================
def export_users_as_excel(queryset, filename: str) -> HttpResponse:
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = [
        "ID", "Name", "Branch", "Channel", "Division", "Part",
        "Grade", "Status", "입사일", "퇴사일", "Is Staff", "Is Active",
    ]
    ws.append(headers)

    for user in queryset:
        ws.append([
            user.id,
            user.name,
            user.branch,
            user.channel,
            user.division,
            user.part,
            GRADE_DISPLAY.get(user.grade, user.grade),
            user.status,
            user.enter.strftime("%Y-%m-%d") if user.enter else "",
            user.quit.strftime("%Y-%m-%d") if user.quit else "",
            user.is_staff,
            user.is_active,
        ])

    response = HttpResponse(content_type=EXCEL_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


def export_selected_users_to_excel(modeladmin, request, queryset):
    return export_users_as_excel(queryset, "selected_custom_users.xlsx")


def export_all_users_excel_view(request):
    return export_users_as_excel(CustomUser.objects.all(), "all_custom_users.xlsx")


# =============================================================================
# 2) Admin Views — Upload / Result / Template
# =============================================================================
def upload_users_from_excel_view(request):
    """
    CustomUser Excel 업로드(Admin View)

    - GET
      업로드 폼 렌더 (task_id가 있으면 진행률 UI도 함께 표시 가능)

    - POST
      1) 업로드 파일을 임시 폴더에 저장
      2) 진행률/상태 cache 초기화
      3) Celery task 실행 (비동기)
      4) task_id를 템플릿에 내려줘서 progress polling 시작
    """
    template_name = "admin/accounts/customuser/upload_excel.html"

    # ---------------------------------------------------------------------
    # 0) task_id (GET으로 재진입/새로고침 등에서 진행률 UI 유지 목적)
    # ---------------------------------------------------------------------
    incoming_task_id = (request.GET.get("task_id") or request.POST.get("task_id") or "").strip()

    # ---------------------------------------------------------------------
    # 1) GET: 업로드 폼
    # ---------------------------------------------------------------------
    if request.method != "POST":
        return render(request, template_name, {
            "form": ExcelUploadForm(),
            "task_id": incoming_task_id,
        })

    # ---------------------------------------------------------------------
    # 2) POST: 폼 검증
    # ---------------------------------------------------------------------
    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, template_name, {
            "form": form,
            "task_id": incoming_task_id,
            "error": "폼이 유효하지 않습니다.",
        })

    excel_file = request.FILES.get("file")
    if not excel_file:
        return render(request, template_name, {
            "form": form,
            "task_id": incoming_task_id,
            "error": "파일이 첨부되지 않았습니다.",
        })

    # ---------------------------------------------------------------------
    # 3) 업로드 작업용 task_id 생성 (POST마다 새로 발급)
    # ---------------------------------------------------------------------
    task_id = uuid.uuid4().hex

    # ---------------------------------------------------------------------
    # 4) 임시 저장 경로 준비 (MEDIA_ROOT가 str이어도 안전하게 Path로 처리)
    # ---------------------------------------------------------------------
    media_root = Path(getattr(settings, "MEDIA_ROOT", "media"))
    default_temp_dir = media_root / "upload_temp"
    temp_dir = Path(getattr(settings, "UPLOAD_TEMP_DIR", default_temp_dir))
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 sanitize (윈도우/리눅스/특수문자 이슈 방지)
    safe_name = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", excel_file.name or "upload.xlsx")

    save_path = temp_dir / f"accounts_upload_{task_id}_{safe_name}"

    # ---------------------------------------------------------------------
    # 5) 파일 저장
    # ---------------------------------------------------------------------
    with open(save_path, "wb") as f:
        for chunk in excel_file.chunks():
            f.write(chunk)

    # ---------------------------------------------------------------------
    # 6) progress cache 초기화 (views.upload_progress_view와 키 규칙 동일)
    # ---------------------------------------------------------------------
    cache_timeout = 60 * 60  # 1 hour
    cache.set(f"upload_progress:{task_id}", 0, timeout=cache_timeout)
    cache.set(f"upload_status:{task_id}", "PENDING", timeout=cache_timeout)
    probe = cache.get(f"upload_status:{task_id}")
    print("DEBUG upload cache probe:", task_id, probe)
    cache.delete(f"upload_error:{task_id}")
    cache.delete(f"upload_result_path:{task_id}")

    # ---------------------------------------------------------------------
    # 7) Celery task 실행 (kwargs 대신 positional로 안전 호출 권장)
    # ---------------------------------------------------------------------
    # tasks.py 시그니처: process_users_excel_task(self, task_id, file_path, batch_size=500)
    process_users_excel_task.delay(task_id, str(save_path), 500)

    # ---------------------------------------------------------------------
    # 8) task_id를 내려서 템플릿에서 progress polling 시작
    # ---------------------------------------------------------------------
    return render(request, template_name, {
        "form": ExcelUploadForm(),
        "task_id": task_id,
        "message": "업로드 작업을 시작했습니다. 진행률을 확인하세요.",
    })


def upload_users_result_view(request, task_id: str):
    path_ = cache.get(f"upload_result_path:{task_id}")
    if not path_ or not os.path.exists(path_):
        raise Http404("결과 파일을 찾을 수 없습니다.")
    return FileResponse(open(path_, "rb"), as_attachment=True, filename=os.path.basename(path_))


def upload_excel_template_view(request):
    abs_path = finders.find(TEMPLATE_REL_PATH)
    if not abs_path or not os.path.exists(abs_path):
        raise Http404("업로드 양식 파일을 찾을 수 없습니다.")
    return FileResponse(
        open(abs_path, "rb"),
        content_type=EXCEL_CONTENT_TYPE,
        as_attachment=True,
        filename=TEMPLATE_DOWNLOAD_NAME,
    )


# =============================================================================
# 3) CustomUser Admin
# =============================================================================
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
            # ✅ change_list.html에서 쓰는 name과 "완전히 동일"하게 맞춤
            path("export-all/", self.admin_site.admin_view(export_all_users_excel_view), name="export_all_users_excel"),
            path("upload-excel/", self.admin_site.admin_view(upload_users_from_excel_view), name="upload_users_excel"),
            path("upload-template/", self.admin_site.admin_view(upload_excel_template_view), name="upload_excel_template"),
            path("upload-result/<str:task_id>/", self.admin_site.admin_view(upload_users_result_view), name="upload_users_result"),
        ]
        return custom_urls + urls
