# django_ma/board/admin.py
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from openpyxl import Workbook
from django.utils.html import format_html
from django.utils.timezone import localtime

from .models import Post
from accounts.custom_admin import custom_admin_site


# ✅ 공통 엑셀 내보내기 함수
def export_posts_as_excel(queryset, filename="posts_export.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Posts"

    headers = [
        '접수번호',
        '제목',
        '사번(요청자)',
        '성명(요청자)',
        '소속(요청자)',
        '성명(대상자)',
        '사번(대상자)',
        '담당자',
        '상태',
        '상태변경일',
        '최초등록일',
    ]
    ws.append(headers)

    for post in queryset:
        ws.append([
            post.receipt_number,
            post.title,
            post.user_id,
            post.user_name,
            post.user_branch,
            post.fa,
            post.code,
            post.handler or '-',
            post.status,
            post.status_updated_at.strftime('%Y-%m-%d %H:%M') if post.status_updated_at else '-',
            localtime(post.created_at).strftime('%Y-%m-%d %H:%M'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@admin.register(Post, site=custom_admin_site)
class PostAdmin(admin.ModelAdmin):
    """게시글 관리자 페이지 설정"""

    # ✅ 목록 표시 필드 (요청자 사번 추가, 컬럼명 한글화)
    list_display = (
        'get_receipt_number',
        'get_category',
        'get_title',
        'get_user_id',
        'get_user_name',
        'get_user_branch',
        'get_fa',
        'get_code',
        'get_handler',
        'colored_status',
        'get_status_updated_at',
        'get_created_at',
    )

    # ✅ 필터 / 검색 / 정렬
    list_filter = ('status', 'handler', 'user_branch', 'category', 'created_at')
    search_fields = ('title', 'content', 'user_name', 'user_id', 'fa', 'code', 'handler')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'status_updated_at', 'receipt_number')

    # ✅ 필드 그룹화
    fieldsets = (
        ('게시글 정보', {
            'fields': ('receipt_number', 'category', 'title', 'content', 'fa', 'code')
        }),
        ('작성자 정보', {
            'fields': ('user_id', 'user_name', 'user_branch')
        }),
        ('담당자 / 상태 관리', {
            'fields': ('handler', 'status', 'status_updated_at')
        }),
        ('기타', {
            'fields': ('created_at',)
        }),
    )

    # ✅ 엑셀 액션 추가
    actions = ['export_selected_posts_to_excel']

    def export_selected_posts_to_excel(self, request, queryset):
        return export_posts_as_excel(queryset, filename="selected_posts.xlsx")
    export_selected_posts_to_excel.short_description = "선택된 게시글을 Excel로 다운로드"

    # ✅ 전체 게시글 내보내기용 URL
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

    def export_all_posts_view(self, request):
        posts = self.model.objects.all()
        return export_posts_as_excel(posts, filename="all_posts.xlsx")

    # ✅ 컬러 상태 표시
    def colored_status(self, obj):
        color_map = {
            '확인중': 'orange',
            '진행중': 'green',
            '보완요청': 'red',
            '완료': 'black',
            '반려': 'gray',
        }
        color = color_map.get(obj.status, 'black')
        return format_html('<span style="color:{}; font-weight:600;">{}</span>', color, obj.status)
    colored_status.short_description = "상태"

    # ✅ 한글 컬럼명 및 커스텀 필드 메서드들
    def get_receipt_number(self, obj):
        return obj.receipt_number
    get_receipt_number.short_description = "접수번호"

    def get_category(self, obj):
        return obj.category
    get_category.short_description = "구분"

    def get_title(self, obj):
        return obj.title
    get_title.short_description = "제목"

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

    def get_handler(self, obj):
        return obj.handler
    get_handler.short_description = "담당자"

    def get_status_updated_at(self, obj):
        if obj.status_updated_at:
            return localtime(obj.status_updated_at).strftime('%Y-%m-%d %H:%M')
        return "-"
    get_status_updated_at.short_description = "상태변경일"

    def get_created_at(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M')
    get_created_at.short_description = "최초등록일"
