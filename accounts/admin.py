# django_ma/accounts/admin.py
# ============================================================
# 📂 관리자 페이지 설정 — CustomUser Excel Import/Export 관리
# ============================================================

import os
from io import BytesIO
from datetime import datetime
from openpyxl import Workbook, load_workbook

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render
from django.urls import path

from .forms import ExcelUploadForm
from .models import CustomUser
from .custom_admin import custom_admin_site


# ============================================================
# ✅ 전역 상수
# ============================================================
EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
UPLOAD_SHEET_NAME = "업로드"
TEMPLATE_FILE_PATH = os.path.join(settings.BASE_DIR, "static", "excel", "업로드양식.xlsx")

GRADE_MAP = {
    'superuser': 'superuser',
    'main_admin': 'main_admin',
    'sub_admin': 'sub_admin',
    'basic': 'basic',
    'inactive': 'inactive',
}

GRADE_DISPLAY = {
    'superuser': 'Superuser',
    'main_admin': 'Main Admin',
    'sub_admin': 'Sub Admin',
    'basic': 'Basic',
    'inactive': 'Inactive',
}


# ============================================================
# ✅ 유틸리티 함수
# ============================================================
def parse_date(value):
    """문자열 또는 datetime 객체를 안전하게 Date 형식으로 변환"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def export_users_as_excel(queryset, filename):
    """사용자 데이터를 엑셀 파일로 내보내기"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = [
        "ID", "Name", "Branch", "Channel", "Part",
        "Grade", "Status", "입사일", "퇴사일", "Is Staff", "Is Active"
    ]
    ws.append(headers)

    for user in queryset:
        ws.append([
            user.id,
            user.name,
            user.branch,
            user.channel,
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

# ============================================================
# ✅ 사용자 업로드 처리 로직
# ============================================================
def upload_users_from_excel_view(request):
    """
    Excel 파일을 업로드하여 사용자 정보를 등록/갱신.
    개선사항:
      ✅ 헤더 기반 매핑 (열 순서와 무관)
      ✅ 결과 리포트 색상 표시 (신규=초록 / 업데이트=회색 / 오류=빨강)
    """
    if request.method != "POST":
        return render(request, "admin/accounts/customuser/upload_excel.html", {"form": ExcelUploadForm()})

    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "admin/accounts/customuser/upload_excel.html", {"form": form, "error": "폼이 유효하지 않습니다."})

    try:
        excel_file = request.FILES["file"]
        wb = load_workbook(excel_file, read_only=True, data_only=True)
        if UPLOAD_SHEET_NAME not in wb.sheetnames:
            raise ValueError(f"'{UPLOAD_SHEET_NAME}' 시트를 찾을 수 없습니다.")

        ws = wb[UPLOAD_SHEET_NAME]
        if ws.sheet_state in ["hidden", "veryHidden"]:
            raise ValueError("'업로드' 시트가 숨김 상태입니다.")

        # ✅ 헤더 로드
        headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
        rows = list(ws.iter_rows(min_row=2, values_only=True))

        results = []
        success_new = success_update = error_count = 0

        # ✅ 한 줄씩 처리
        for idx, row in enumerate(rows, start=2):
            row_data = dict(zip(headers, row))
            user_id = str(row_data.get("사번") or "").strip()
            name = str(row_data.get("성명") or "").strip()
            if not user_id or not name:
                results.append([idx, user_id, name, "❌ ID 또는 이름 누락"])
                error_count += 1
                continue

            grade_val = GRADE_MAP.get(str(row_data.get("등급") or "").lower(), "basic")
            status_val = str(row_data.get("상태") or "재직").strip()
            is_superuser = grade_val == "superuser"
            is_staff = grade_val in ["superuser", "main_admin", "sub_admin"]
            is_active = status_val == "재직"

            defaults = dict(
                name=name,
                channel=str(row_data.get("채널") or "").strip(),
                part=str(row_data.get("부서") or "").strip(),
                branch=str(row_data.get("지점") or "").strip(),
                grade=grade_val,
                status=status_val,
                regist=str(row_data.get("손생등록여부") or "").strip(),
                birth=parse_date(row_data.get("생년월일")),
                enter=parse_date(row_data.get("입사일")),
                quit=parse_date(row_data.get("퇴사일")),
                is_active=is_active,
                is_staff=is_staff,
                is_superuser=is_superuser,
            )

            try:
                user = CustomUser.objects.filter(id=user_id).first()
                if user:
                    for k, v in defaults.items():
                        setattr(user, k, v)
                    user.save()
                    success_update += 1
                    results.append([idx, user_id, name, "✅ 기존 업데이트"])
                else:
                    CustomUser.objects.create_user(
                        id=user_id,
                        password=str(row_data.get("비밀번호") or user_id),
                        **defaults
                    )
                    success_new += 1
                    results.append([idx, user_id, name, "🟢 신규 등록"])
            except Exception as e:
                error_count += 1
                results.append([idx, user_id, name, f"❌ 오류: {e}"])

        # ✅ 결과 리포트 생성
        result_wb = Workbook()
        ws_result = result_wb.active
        ws_result.title = "UploadResult"

        ws_result.append(["Row", "ID", "Name", "Result"])

        from openpyxl.styles import PatternFill

        fill_new = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")   # 연녹색
        fill_update = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid") # 연회색
        fill_error = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # 연분홍

        for row_data in results:
            ws_result.append(row_data)
            last_row = ws_result.max_row
            result_text = str(row_data[-1])
            if "신규" in result_text:
                ws_result[f"D{last_row}"].fill = fill_new
            elif "업데이트" in result_text:
                ws_result[f"D{last_row}"].fill = fill_update
            elif "오류" in result_text or "누락" in result_text:
                ws_result[f"D{last_row}"].fill = fill_error

        # ✅ 요약 정보
        ws_result.append([])
        ws_result.append(["총 데이터", len(rows)])
        ws_result.append(["신규 추가", success_new])
        ws_result.append(["업데이트", success_update])
        ws_result.append(["오류", error_count])

        # ✅ 파일 응답
        output = BytesIO()
        result_wb.save(output)
        output.seek(0)
        filename = f"upload_result_{datetime.now():%Y%m%d_%H%M}.xlsx"

        response = HttpResponse(output.getvalue(), content_type=EXCEL_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f"Excel 파일 처리 중 오류: {e}")
        return render(request, "admin/accounts/customuser/upload_excel.html", {"form": ExcelUploadForm()})



# ============================================================
# ✅ 기타 유틸 뷰
# ============================================================
def export_selected_users_to_excel(modeladmin, request, queryset):
    """선택된 사용자만 엑셀로 다운로드"""
    return export_users_as_excel(queryset, filename="selected_custom_users.xlsx")


def export_all_users_excel_view(request):
    """전체 사용자 엑셀 다운로드"""
    return export_users_as_excel(CustomUser.objects.all(), filename="all_custom_users.xlsx")


def upload_excel_template_view(request):
    """업로드용 양식 파일 다운로드"""
    if not os.path.exists(TEMPLATE_FILE_PATH):
        raise Http404("업로드 양식 파일을 찾을 수 없습니다.")
    return FileResponse(
        open(TEMPLATE_FILE_PATH, "rb"),
        content_type=EXCEL_CONTENT_TYPE,
        as_attachment=True,
        filename="업로드양식.xlsx"
    )


# ============================================================
# ✅ 관리자 페이지 커스터마이징
# ============================================================
@admin.register(CustomUser)
@admin.register(CustomUser, site=custom_admin_site)
class CustomUserAdmin(UserAdmin):
    """CustomUser 모델용 관리자 설정"""
    model = CustomUser
    actions = [export_selected_users_to_excel]

    list_display = (
        "id", "name", "channel", "part", "branch",
        "grade", "status", "enter", "quit",
        "is_staff", "is_active",
    )
    search_fields = ("id", "name", "branch")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("id", "password")}),
        ("Personal Info", {"fields": (
            "name", "channel", "part", "branch",
            "grade", "status", "enter", "quit",
        )}),
        ("Permissions", {"fields": (
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions"
        )}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "id", "password1", "password2",
                "name", "channel", "part", "branch",
                "grade", "status", "enter", "quit",
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        """퇴사일 입력 시 자동으로 상태(status)를 '퇴사'로 변경"""
        if obj.quit:
            obj.status = "퇴사"
        super().save_model(request, obj, form, change)

    def get_urls(self):
        """엑셀 업로드/다운로드용 커스텀 URL 등록"""
        urls = super().get_urls()
        custom_urls = [
            path("export-all/", self.admin_site.admin_view(export_all_users_excel_view), name="export_all_users_excel"),
            path("upload-excel/", self.admin_site.admin_view(upload_users_from_excel_view), name="upload_users_excel"),
            path("upload-template/", self.admin_site.admin_view(upload_excel_template_view), name="upload_excel_template"),
        ]
        return custom_urls + urls

    change_list_template = "admin/accounts/customuser/change_list.html"