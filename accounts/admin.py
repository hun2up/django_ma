from openpyxl import Workbook
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from .models import CustomUser

def export_users_to_excel(modeladmin, request, queryset):
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
    response['Content-Disposition'] = 'attachment; filename=custom_users.xlsx'
    wb.save(response)
    return response

export_users_to_excel.short_description = "Download to Excel"  # admin에 표시될 이름

# ✅ 이미 데코레이터로 등록했기 때문에 아래 한 줄만 있으면 됩니다
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    actions = [export_users_to_excel]
    list_display = ('id', 'name', 'branch', 'grade', 'status', 'is_staff', 'is_active')
    search_fields = ('id', 'name', 'branch')
    ordering = ('id',)

    fieldsets = (
        (None, {'fields': ('id', 'password')}),
        ('개인 정보', {'fields': ('name', 'branch', 'grade', 'status')}),
        ('권한 설정', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('id', 'password1', 'password2', 'name', 'branch', 'grade', 'status'),
        }),
    )
