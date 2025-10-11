from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
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
