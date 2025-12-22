# django_ma/accounts/admin.py
# ============================================================
# 📂 관리자 페이지 설정 — CustomUser Excel Import/Export 관리
# ============================================================

from __future__ import annotations

import os
from io import BytesIO
from datetime import datetime, date

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.staticfiles import finders
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

# ✅ 템플릿 파일 (앱 static 기준)
TEMPLATE_REL_PATH = "accounts/excel/양식_계정관리.xlsx"  # accounts/static/accounts/excel/양식_계정관리.xlsx
TEMPLATE_DOWNLOAD_NAME = "양식_계정관리.xlsx"

GRADE_MAP = {
    "superuser": "superuser",
    "main_admin": "main_admin",
    "sub_admin": "sub_admin",
    "basic": "basic",
    "inactive": "inactive",
}

GRADE_DISPLAY = {
    "superuser": "Superuser",
    "main_admin": "Main Admin",
    "sub_admin": "Sub Admin",
    "basic": "Basic",
    "inactive": "Inactive",
}


# ============================================================
# ✅ 유틸리티 함수
# ============================================================
def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()


def parse_date(value) -> date | None:
    """문자열 또는 datetime/date 객체를 안전하게 date로 변환"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = _to_str(value)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_bool(value, default: bool = True) -> bool:
    """엑셀에서 들어올 수 있는 다양한 bool 표현을 안전하게 파싱"""
    s = _to_str(value).lower()
    if s in {"true", "1", "yes", "y", "t"}:
        return True
    if s in {"false", "0", "no", "n", "f"}:
        return False
    return default


def export_users_as_excel(queryset, filename: str) -> HttpResponse:
    """사용자 데이터를 엑셀 파일로 내보내기"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = [
        "ID", "Name", "Branch", "Channel", "Part",
        "Grade", "Status", "입사일", "퇴사일", "Is Staff", "Is Active",
    ]
    ws.append(headers)

    for user in queryset:
        ws.append([
            user.id,
            user.name,
            user.branch,
            getattr(user, "channel", ""),
            getattr(user, "part", ""),
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


def _make_upload_result_workbook(
    results: list[list],
    total: int,
    new_cnt: int,
    upd_cnt: int,
    err_cnt: int,
) -> Workbook:
    """업로드 처리 결과 리포트 엑셀 생성"""
    result_wb = Workbook()
    ws = result_wb.active
    ws.title = "UploadResult"

    ws.append(["Row", "ID", "Name", "Result"])

    fill_new = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")      # 연녹색
    fill_update = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")  # 연회색
    fill_error = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")   # 연분홍

    for row in results:
        ws.append(row)
        last = ws.max_row
        result_text = _to_str(row[-1])

        if "신규" in result_text:
            ws[f"D{last}"].fill = fill_new
        elif "업데이트" in result_text:
            ws[f"D{last}"].fill = fill_update
        elif "오류" in result_text or "누락" in result_text:
            ws[f"D{last}"].fill = fill_error

    ws.append([])
    ws.append(["총 데이터", total])
    ws.append(["신규 추가", new_cnt])
    ws.append(["업데이트", upd_cnt])
    ws.append(["오류", err_cnt])

    return result_wb


def _load_upload_sheet(excel_file):
    """
    업로드 엑셀 파일에서 '업로드' 시트를 열고,
    (headers, worksheet) 반환
    - ✅ rows를 list로 만들지 않음(대용량 대비)
    """
    wb = load_workbook(excel_file, read_only=True, data_only=True)

    if UPLOAD_SHEET_NAME not in wb.sheetnames:
        raise ValueError(f"'{UPLOAD_SHEET_NAME}' 시트를 찾을 수 없습니다.")

    ws = wb[UPLOAD_SHEET_NAME]

    if ws.sheet_state in ["hidden", "veryHidden"]:
        raise ValueError("'업로드' 시트가 숨김 상태입니다.")

    headers = [_to_str(c.value) for c in ws[1]]
    return headers, ws


# ============================================================
# ✅ 사용자 업로드 처리 로직 (Admin View)
# ============================================================
def upload_users_from_excel_view(request):
    if request.method != "POST":
        return render(request, "admin/accounts/customuser/upload_excel.html", {"form": ExcelUploadForm()})

    form = ExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "admin/accounts/customuser/upload_excel.html",
            {"form": form, "error": "폼이 유효하지 않습니다."},
        )

    try:
        excel_file = request.FILES["file"]
        headers, ws = _load_upload_sheet(excel_file)

        results: list[list] = []
        success_new = 0
        success_update = 0
        error_count = 0
        total = 0

        # ✅ rows를 메모리에 올리지 않고 스트리밍 처리
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            total += 1
            row_data = dict(zip(headers, row))

            user_id = _to_str(row_data.get("사번"))
            name = _to_str(row_data.get("성명"))

            if not user_id or not name:
                results.append([idx, user_id, name, "❌ ID 또는 이름 누락"])
                error_count += 1
                continue

            grade_raw = _to_str(row_data.get("등급")).lower()
            grade_val = GRADE_MAP.get(grade_raw, "basic")

            status_val = _to_str(row_data.get("상태")) or "재직"
            is_superuser = grade_val == "superuser"
            is_staff = grade_val in {"superuser", "main_admin", "sub_admin"}

            # ✅ IS_ACTIVE / is_active 둘 다 지원
            is_active_cell = row_data.get("IS_ACTIVE")
            if is_active_cell is None:
                is_active_cell = row_data.get("is_active")
            is_active = parse_bool(is_active_cell, default=True)

            defaults = dict(
                name=name,
                channel=_to_str(row_data.get("채널")),
                part=_to_str(row_data.get("부서")),
                branch=_to_str(row_data.get("지점")),
                grade=grade_val,
                status=status_val,
                regist=_to_str(row_data.get("손생등록여부")),
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
                        password=_to_str(row_data.get("비밀번호")) or user_id,
                        **defaults,
                    )
                    success_new += 1
                    results.append([idx, user_id, name, "🟢 신규 등록"])

            except Exception as e:
                error_count += 1
                results.append([idx, user_id, name, f"❌ 오류: {e}"])

        result_wb = _make_upload_result_workbook(
            results=results,
            total=total,
            new_cnt=success_new,
            upd_cnt=success_update,
            err_cnt=error_count,
        )

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
    return export_users_as_excel(queryset, filename="selected_custom_users.xlsx")


def export_all_users_excel_view(request):
    return export_users_as_excel(CustomUser.objects.all(), filename="all_custom_users.xlsx")


def upload_excel_template_view(request):
    """
    업로드용 양식 파일 다운로드
    - accounts/static/accounts/excel/양식_계정관리.xlsx 를 찾아 내려줌
    - 배포/collectstatic 환경에서도 동작하도록 staticfiles finders 사용
    """
    abs_path = finders.find(TEMPLATE_REL_PATH)
    if not abs_path or not os.path.exists(abs_path):
        raise Http404("업로드 양식 파일을 찾을 수 없습니다.")

    return FileResponse(
        open(abs_path, "rb"),
        content_type=EXCEL_CONTENT_TYPE,
        as_attachment=True,
        filename=TEMPLATE_DOWNLOAD_NAME,
    )


# ============================================================
# ✅ 관리자 페이지 커스터마이징
# ============================================================
@admin.register(CustomUser)
@admin.register(CustomUser, site=custom_admin_site)
class CustomUserAdmin(UserAdmin):
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
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
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
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-all/",
                self.admin_site.admin_view(export_all_users_excel_view),
                name="export_all_users_excel",
            ),
            path(
                "upload-excel/",
                self.admin_site.admin_view(upload_users_from_excel_view),
                name="upload_users_excel",
            ),
            path(
                "upload-template/",
                self.admin_site.admin_view(upload_excel_template_view),
                name="upload_excel_template",
            ),
        ]
        return custom_urls + urls

    change_list_template = "admin/accounts/customuser/change_list.html"
