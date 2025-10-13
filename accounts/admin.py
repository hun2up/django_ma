from openpyxl import Workbook
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from .models import CustomUser
from .forms import ExcelUploadForm

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


def upload_users_from_excel_view(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES["file"]
            wb = load_workbook(excel_file)
            ws = wb.active

            # assume first row is header
            for row in ws.iter_rows(min_row=2, values_only=True):
                user_id, password, name, branch, grade, status = row[:6]
                try:
                    CustomUser.objects.create_user(
                        id=user_id,
                        password=password,
                        name=name,
                        branch=branch,
                        grade=grade,
                        status=status,
                    )
                except Exception as e:
                    messages.error(request, f"Error on row {row}: {str(e)}")
                    continue

            messages.success(request, "Users uploaded successfully.")
            return redirect("..")
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

    # 관리자 액션 등록
    actions = [export_selected_users_to_excel]

    # 리스트 설정
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

    # ✅ 커스텀 URL 등록 (버튼 클릭용)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-all/', self.admin_site.admin_view(export_all_users_excel_view), name='export_all_users_excel'),
            path('upload-excel/', self.admin_site.admin_view(upload_users_from_excel_view), name='upload_users_excel'),
        ]
        return custom_urls + urls

    # ✅ custom change_list.html 사용
    change_list_template = "admin/accounts/customuser/change_list.html"
