from openpyxl import Workbook, load_workbook
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ExcelUploadForm
from .models import CustomUser

# ✅ 공통 엑셀 생성 함수
def export_users_as_excel(queryset, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    # 헤더 작성
    headers = ['ID', 'Name', 'Branch', 'Grade', 'Status', 'Is Staff', 'Is Active']
    ws.append(headers)

    # 데이터 작성
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

    # 응답 설정
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
                ws = wb.active  # 첫 번째 시트만 사용

                success_count = 0
                error_count = 0
                max_error_log = 5

                for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    if not row or len(row) < 6:
                        if error_count < max_error_log:
                            messages.error(request, f"Row {idx}: 데이터가 부족합니다.")
                        error_count += 1
                        continue

                    # ✅ 데이터 언팩 및 기본 정리
                    user_id = str(row[0]).strip() if row[0] else ""
                    password = str(row[1]) if row[1] is not None else ""
                    name = row[2]
                    branch = row[3]
                    grade = str(row[4]).strip() if row[4] else ""
                    status = str(row[5]).strip() if row[5] else ""

                    # ✅ 이름 유효성 검사
                    name_str = str(name).strip() if name is not None else ""
                    if not name_str or name_str == "0" or isinstance(name, (int, float)):
                        if error_count < max_error_log:
                            messages.error(request, f"Row {idx}: 이름이 비정상입니다. → {name}")
                        error_count += 1
                        continue

                    # ✅ ID 중복 방지
                    if not user_id or CustomUser.objects.filter(id=user_id).exists():
                        continue

                    # ✅ 권한 자동 설정
                    is_superuser = grade.lower() == 'superuser'
                    is_staff = grade.lower() in ['superuser', 'admin']
                    is_active = status == '재직'

                    try:
                        CustomUser.objects.create_user(
                            id=user_id,
                            password=password,
                            name=name_str,
                            branch=branch,
                            grade=grade,
                            status=status,
                            is_active=is_active,
                            is_staff=is_staff,
                            is_superuser=is_superuser,
                        )
                        success_count += 1
                    except Exception as e:
                        if error_count < max_error_log:
                            messages.error(request, f"Row {idx}: {str(e)}")
                        error_count += 1

                messages.success(
                    request,
                    f"{success_count}명 등록 성공, {error_count}건 오류 발생"
                )
                return redirect("..")

            except Exception as e:
                messages.error(request, f"Excel 파일 처리 중 오류: {str(e)}")
    else:
        form = ExcelUploadForm()

    return render(request, "admin/accounts/customuser/upload_excel.html", {"form": form})


# ✅ 선택된 사용자만 엑셀로 다운로드 (Action)
def export_selected_users_to_excel(modeladmin, request, queryset):
    return export_users_as_excel(queryset, filename="selected_custom_users.xlsx")
export_selected_users_to_excel.short_description = "Download selected users to Excel"

# ✅ 전체 사용자 엑셀 다운로드 (버튼 전용)
def export_all_users_excel_view(request):
    users = CustomUser.objects.all()
    return export_users_as_excel(users, filename="all_custom_users.xlsx")

# ✅ 관리자 등록
@admin.register(CustomUser)
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
