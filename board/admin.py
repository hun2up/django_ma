# django_ma/board/admin.py
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from openpyxl import Workbook

from .models import Post
from accounts.custom_admin import custom_admin_site


def export_posts_as_excel(queryset, filename="posts_export.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Posts"

    headers = [
        'ID',
        '제목',
        '사번',
        '대상자(성명)',     # user_name
        '요청자(소속)',     # user_branch
        '대상자(성명)',     # fa
        '대상자(사번)',     # code
        '요청일시',         # created_at
    ]
    ws.append(headers)

    for post in queryset:
        ws.append([
            post.id,
            post.title,
            post.user_id,
            post.user_name,
            post.user_branch,
            post.fa,
            post.code,
            post.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@admin.register(Post, site=custom_admin_site)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'get_user_id',    # 사번
        'get_user_name',  # 대상자(성명)
        'get_user_branch',# 요청자(소속)
        'get_fa',         # 대상자(성명)
        'get_code',       # 대상자(사번)
        'get_created_at', # 요청일시
    )
    list_filter = ('category', 'user_branch', 'created_at')
    search_fields = ('title', 'content', 'user_name', 'user_id', 'fa', 'code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('게시글 정보', {
            'fields': ('title', 'content', 'category', 'fa', 'code'),
        }),
        ('작성자 정보', {
            'fields': ('user_id', 'user_name', 'user_branch'),
        }),
        ('기타', {
            'fields': ('created_at',),
        }),
    )

    actions = ['export_selected_posts_to_excel']

    def export_selected_posts_to_excel(self, request, queryset):
        return export_posts_as_excel(queryset, filename="selected_posts.xlsx")
    export_selected_posts_to_excel.short_description = "Download selected posts to excel"

    def export_all_posts_view(self, request):
        posts = self.model.objects.all()
        return export_posts_as_excel(posts, filename="all_posts.xlsx")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-all/',
                self.admin_site.admin_view(self.export_all_posts_view),
                name='export_all_posts_excel',
            ),
        ]
        return custom_urls + urls

    # ✅ 사용자 정의 컬럼 출력 메서드들 (컬럼명 포함)
    def get_user_id(self, obj):
        return obj.user_id
    get_user_id.short_description = "사번(요청자)"

    def get_user_name(self, obj):
        return obj.user_name
    get_user_name.short_description = "성명(요청자)"

    def get_user_branch(self, obj):
        return obj.user_branch
    get_user_branch.short_description = "소속(요청자)"

    def get_fa(self, obj):
        return obj.fa
    get_fa.short_description = "성명(대상자)"

    def get_code(self, obj):
        return obj.code
    get_code.short_description = "사번(대상자)"

    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    get_created_at.short_description = "요청일시"
