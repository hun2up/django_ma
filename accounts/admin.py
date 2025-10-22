# django_ma/accounts/admin.py
from openpyxl import Workbook, load_workbook
from io import BytesIO
from datetime import datetime
import os

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import render, redirect
from django.urls import path

from .forms import ExcelUploadForm
from .models import CustomUser
from .custom_admin import custom_admin_site


# ============================================================
# ✅ 상수 정의
# ============================================================
GRADE_MAP = {
    'superuser': 'superuser',
    'mainadmin': 'main_admin',
    'main_admin': 'main_admin',
    'subadmin': 'sub_admin',
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
    """문자열 또는 datetime을 안전하게 날짜로 변환"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def export_users_as_excel(queryset, filename):
    """사용자 데이터를 엑셀 파일로 내보내기"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"
    ws.append(['ID', 'Name', 'Branch', 'Grade', 'Status', '입사일', '퇴사일', 'Is Staff', 'Is Active'])

    for user in queryset:
        ws.append([
            user.id,
            user.name,
            user.branch,
            GRADE_DISPLAY.get(user.grade, user.grade),
            user.status,
            user.enter.strftime("%Y-%m-%d") if user.enter else "",
            user.quit.strftime("%Y-%m-%d") if user.quit else "",
            user.is_staff,
            user.is_active,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


# ============================================================
# ✅ 엑셀 업로드 로직
# ============================================================
def upload_users_from_excel_view(request):
    """Excel 파일을 업로드하여 사용자 정보를 등록 또는 갱신"""
    if request.method != "POST":
        return render(request, "admin/accounts/customuser/upload_excel.html", {"form": ExcelUploadForm()})

    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "업로드 폼이 유효하지 않습니다.")
        return redirect("..")

    try:
        excel_file = request.FILES["file"]
        wb = load_workbook(excel_file, read_only=True, data_only=True)

        # --- 시트 확인 ---
        if "업로드" not in wb.sheetnames:
            messages.error(request, "'업로드' 시트를 찾을 수 없습니다. 양식을 다시 확인하세요.")
            return redirect("..")

        ws = wb["업로드"]
        if ws.sheet_state in ["hidden", "veryHidden"]:
            messages.error(request, "'업로드' 시트가 숨김 상태입니다. 숨김 해제 후 업로드하세요.")
            return redirect("..")

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        total_rows = len(rows)
        success_new, success_update, error_count = 0, 0, 0
        results = []

        # --- 중복 Main Admin 검사 ---
        branch_admin_count = {}
        for row in rows:
            if not row or len(row) < 12:
                continue
            _, _, _, branch, grade, *_ = row
            if not branch or not grade:
                continue
            if GRADE_MAP.get(str(grade).strip().lower()) == "main_admin":
                branch_name = str(branch).strip()
                branch_admin_count[branch_name] = branch_admin_count.get(branch_name, 0) + 1

        duplicate_branches = [b for b, count in branch_admin_count.items() if count > 1]
        if duplicate_branches:
            messages.error(request, f"동일 영업가족 내에 둘 이상의 최상위관리자를 지정할 수 없습니다: {', '.join(duplicate_branches)}")
            return redirect("..")

        # --- 사용자 등록/갱신 ---
        for idx, row in enumerate(rows, start=2):
            if not row or len(row) < 12:
                results.append([idx, None, None, "데이터 부족"])
                error_count += 1
                continue

            (
                user_id, password, name, branch, grade,
                status, *_,
                regist, birth, enter, quit_date
            ) = row[:12]

            if not user_id or not name:
                results.append([idx, user_id, name, "ID 또는 이름 누락"])
                error_count += 1
                continue

            grade_val = GRADE_MAP.get(str(grade).strip().lower(), "basic")
            is_superuser = grade_val == "superuser"
            is_staff = grade_val in ["superuser", "main_admin", "sub_admin"]
            is_active = str(status).strip() == "재직"

            try:
                user = CustomUser.objects.filter(id=user_id).first()
                defaults = dict(
                    name=str(name).strip(),
                    branch=str(branch).strip() if branch else "",
                    grade=grade_val,
                    status=str(status).strip() or "재직",
                    regist=str(regist).strip() if regist else "",
                    birth=parse_date(birth),
                    enter=parse_date(enter),
                    quit=parse_date(quit_date),
                    is_active=is_active,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                )

                if user:
                    for key, val in defaults.items():
                        setattr(user, key, val)
                    user.save()
                    success_update += 1
                    results.append([idx, user_id, name, "기존 업데이트"])
                else:
                    CustomUser.objects.create_user(
                        id=str(user_id).strip(),
                        password=str(password or user_id).strip(),
                        **defaults
                    )
                    success_new += 1
                    results.append([idx, user_id, name, "신규 등록"])

            except Exception as e:
                error_count += 1
                results.append([idx, user_id, name, f"오류: {e}"])

        # --- 결과 요약 엑셀 생성 ---
        result_wb = Workbook()
        ws = result_wb.active
        ws.title = "UploadResult"
        ws.append(["Row", "ID", "Name", "Result"])
        for row in results:
            ws.append(row)

        ws.append([])
        ws.append(["총 데이터", total_rows])
        ws.append(["신규 추가", success_new])
        ws.append(["업데이트", success_update])
        ws.append(["오류", error_count])

        output = BytesIO()
        result_wb.save(output)
        output.seek(0)

        filename = f"upload_result_{datetime.now():%Y%m%d_%H%M}.xlsx"
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        messages.error(request, f"Excel 파일 처리 중 오류: {e}")
        return redirect("..")


# ============================================================
# ✅ 기타 유틸 뷰
# ============================================================
def export_selected_users_to_excel(modeladmin, request, queryset):
    return export_users_as_excel(queryset, filename="selected_custom_users.xlsx")
export_selected_users_to_excel.short_description = "선택된 사용자 엑셀 다운로드"


def export_all_users_excel_view(request):
    users = CustomUser.objects.all()
    return export_users_as_excel(users, filename="all_custom_users.xlsx")


def upload_excel_template_view(request):
    path = os.path.join(settings.BASE_DIR, "static", "excel", "업로드양식.xlsx")
    if not os.path.exists(path):
        raise Http404("양식 파일을 찾을 수 없습니다. 관리자에게 문의하세요.")
    return FileResponse(
        open(path, "rb"),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        filename="업로드양식.xlsx"
    )


# ============================================================
# ✅ 관리자 등록 (입사일/퇴사일 + 자동 상태 업데이트 포함)
# ============================================================
@admin.register(CustomUser)
@admin.register(CustomUser, site=custom_admin_site)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    actions = [export_selected_users_to_excel]

    # ✅ 목록에 입사일/퇴사일 표시
    list_display = (
        "id", "name", "branch", "grade", "status",
        "enter", "quit",  # ✅ 추가됨
        "is_staff", "is_active",
    )
    search_fields = ("id", "name", "branch")
    ordering = ("id",)

    # ✅ 상세페이지에서 입사일/퇴사일 수정 가능
    fieldsets = (
        (None, {"fields": ("id", "password")}),
        ("Personal Info", {
            "fields": (
                "name", "branch", "grade", "status",
                "enter", "quit",  # ✅ 추가됨
            )
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "id", "password1", "password2",
                "name", "branch", "grade", "status",
                "enter", "quit",
            ),
        }),
    )

    # ✅ 퇴사일 입력 시 자동으로 status='퇴사' 처리
    def save_model(self, request, obj, form, change):
        """퇴사일 입력 시 자동으로 상태(status)를 '퇴사'로 변경"""
        if obj.quit:
            obj.status = "퇴사"
            # 비활성화까지 함께 처리하고 싶다면 아래 두 줄도 추가 가능
            # obj.is_active = False
            # obj.is_staff = False
        super().save_model(request, obj, form, change)

    # ✅ 커스텀 URL (엑셀 다운로드/업로드)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("export-all/", self.admin_site.admin_view(export_all_users_excel_view), name="export_all_users_excel"),
            path("upload-excel/", self.admin_site.admin_view(upload_users_from_excel_view), name="upload_users_excel"),
            path("upload-template/", self.admin_site.admin_view(upload_excel_template_view), name="upload_excel_template"),
        ]
        return custom_urls + urls

    change_list_template = "admin/accounts/customuser/change_list.html"
