# django_ma/accounts/admin.py
from openpyxl import Workbook, load_workbook
from io import BytesIO
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ExcelUploadForm
from .models import CustomUser
from .custom_admin import custom_admin_site
from datetime import datetime


# ✅ 공통 엑셀 생성 함수
def export_users_as_excel(queryset, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = ['ID', 'Name', 'Branch', 'Grade', 'Status', 'Is Staff', 'Is Active']
    ws.append(headers)

    for user in queryset:
        ws.append([
            user.id,
            user.name,
            user.branch,
            user.grade,
            user.status,
            user.is_staff,
            user.is_active,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


# ✅ 엑셀 업로드 처리
def upload_users_from_excel_view(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["file"]
            try:
                wb = load_workbook(excel_file, read_only=True, data_only=True)

                # ✅ “업로드” 시트 존재 확인
                if "업로드" not in wb.sheetnames:
                    messages.error(request, "'업로드' 시트를 찾을 수 없습니다. 업로드 양식을 다시 확인해주세요.")
                    return redirect("..")

                ws = wb["업로드"]

                # ✅ 시트 숨김 상태 확인
                if ws.sheet_state in ["hidden", "veryHidden"]:
                    messages.error(request, "'업로드' 시트가 숨김 상태입니다. 숨김 해제 후 다시 업로드하세요.")
                    return redirect("..")

                total_rows = ws.max_row - 1
                success_new, success_update, error_count = 0, 0, 0
                results = []

                def parse_date(val):
                    if not val:
                        return None
                    if isinstance(val, datetime):
                        return val.date()
                    try:
                        return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
                    except Exception:
                        return None

                # ✅ 각 행 반복 처리
                for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not row or len(row) < 12:
                        error_count += 1
                        results.append([idx, None, None, "데이터 부족"])
                        continue

                    (
                        user_id, password, name, branch, grade,
                        status, is_staff_val, is_active_val,
                        regist, birth, enter, quit_date
                    ) = row[:12]

                    if not user_id or not name:
                        error_count += 1
                        results.append([idx, user_id, name, "ID 또는 이름 누락"])
                        continue

                    grade = str(grade).strip().lower() if grade else "basic"
                    is_superuser = grade == "superuser"
                    is_staff = grade in ["superuser", "admin"]
                    is_active = status == "재직"

                    try:
                        user = CustomUser.objects.filter(id=user_id).first()

                        if user is None:
                            # 신규 등록
                            CustomUser.objects.create_user(
                                id=str(user_id).strip(),
                                password=str(user_id).strip(),
                                name=str(name).strip(),
                                branch=str(branch).strip() if branch else "",
                                grade=grade,
                                status=str(status).strip() if status else "재직",
                                regist=str(regist).strip() if regist else "",
                                birth=parse_date(birth),
                                enter=parse_date(enter),
                                quit=parse_date(quit_date),
                                is_active=is_active,
                                is_staff=is_staff,
                                is_superuser=is_superuser,
                            )
                            success_new += 1
                            results.append([idx, user_id, name, "신규 등록"])
                        else:
                            # 기존 사용자 업데이트
                            user.name = str(name).strip()
                            user.branch = str(branch).strip() if branch else ""
                            user.grade = grade
                            user.status = str(status).strip() if status else user.status
                            user.regist = str(regist).strip() if regist else user.regist
                            user.birth = parse_date(birth)
                            user.enter = parse_date(enter)
                            user.quit = parse_date(quit_date)
                            user.is_active = is_active
                            user.is_staff = is_staff
                            user.is_superuser = is_superuser
                            user.save()
                            success_update += 1
                            results.append([idx, user_id, name, "기존 업데이트"])

                    except Exception as e:
                        error_count += 1
                        results.append([idx, user_id, name, str(e)])

                # ✅ 결과 엑셀 생성
                result_wb = Workbook()
                result_ws = result_wb.active
                result_ws.title = "UploadResult"
                result_ws.append(["Row", "ID", "Name", "Result"])

                for row in results:
                    result_ws.append(row)

                summary = [
                    [],
                    ["총 데이터", total_rows],
                    ["신규 추가", success_new],
                    ["업데이트", success_update],
                    ["오류", error_count],
                ]
                for row in summary:
                    result_ws.append(row)

                output = BytesIO()
                result_wb.save(output)
                output.seek(0)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"upload_result_{timestamp}.xlsx"

                response = HttpResponse(
                    output.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename={filename}'
                return response

            except Exception as e:
                messages.error(request, f"Excel 파일 처리 중 오류: {str(e)}")

    else:
        form = ExcelUploadForm()

    return render(request, "admin/accounts/customuser/upload_excel.html", {"form": form})


# ✅ 선택된 사용자만 엑셀로 다운로드 (Action)
def export_selected_users_to_excel(modeladmin, request, queryset):
    return export_users_as_excel(queryset, filename="selected_custom_users.xlsx")
export_selected_users_to_excel.short_description = "Download selected users to Excel"


# ✅ 전체 사용자 엑셀 다운로드
def export_all_users_excel_view(request):
    users = CustomUser.objects.all()
    return export_users_as_excel(users, filename="all_custom_users.xlsx")


# ✅ 관리자 등록
@admin.register(CustomUser)
@admin.register(CustomUser, site=custom_admin_site)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    actions = [export_selected_users_to_excel]

    list_display = ('id', 'name', 'branch', 'grade', 'status', 'is_staff', 'is_active')
    search_fields = ('id', 'name', 'branch')
    ordering = ('id',)

    fieldsets = (
        (None, {'fields': ('id', 'password')}),
        ('Personal Info', {'fields': ('name', 'branch', 'grade', 'status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('id', 'password1', 'password2', 'name', 'branch', 'grade', 'status'),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-all/', self.admin_site.admin_view(export_all_users_excel_view), name='export_all_users_excel'),
            path('upload-excel/', self.admin_site.admin_view(upload_users_from_excel_view), name='upload_users_excel'),
        ]
        return custom_urls + urls

    change_list_template = "admin/accounts/customuser/change_list.html"
