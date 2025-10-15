from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from openpyxl import Workbook

from .models import JoinInfo
from accounts.custom_admin import custom_admin_site


# ✅ 엑셀 생성 함수
def export_joininfo_as_excel(queryset, filename="joininfo_export.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Join Info"

    headers = [
        'ID',
        '요청자(사번)',
        '요청자(성명)',
        '요청자(소속)',
        '대사자(성명)',
        '대상자(주민번호)',
        '대상자(전화번호)',
        '대상자(우편번호)',
        '대상자(주소)',
        '대상자(상세주소)',
        '대상자(이메일)',
        '등록일시',
    ]
    ws.append(headers)

    for join in queryset:
        ws.append([
            join.id,
            join.user_id,
            join.user_name,
            join.user_branch,
            join.name,
            join.ssn,
            join.phone,
            join.postcode,
            join.address,
            join.address_detail,
            join.email,
            join.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    wb.save(response)
    return response


@admin.register(JoinInfo)
@admin.register(JoinInfo, site=custom_admin_site)
class JoinInfoAdmin(admin.ModelAdmin):
    change_list_template = "admin/join/joininfo/change_list.html"

    # ✅ 원하는 순서대로 사용자 정의 메서드들을 list_display에 등록
    list_display = (
        'user_id_display',
        'user_name_display',
        'user_branch_display',
        'name_display',
        'ssn_display',
        'postcode_display',
        'address_display',
        'address_detail_display',
        'phone_display',
        'email_display',
        'created_at_display',
    )

    search_fields = ('name', 'email', 'phone')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    fields = (
        'name',
        'ssn',
        'postcode',
        'address',
        'address_detail',
        'phone',
        'email',
    )
    readonly_fields = ('created_at',)
    actions = ['export_selected_joininfo_to_excel']

    # ✅ 사용자 정의 메서드들 및 컬럼 헤더 수정
    def user_id_display(self, obj):
        return obj.user_id
    user_id_display.short_description = "사번(요청자)"

    def user_name_display(self, obj):
        return obj.user_name
    user_name_display.short_description = "성명(요청자)"

    def user_branch_display(self, obj):
        return obj.user_branch
    user_branch_display.short_description = "소속(요청자)"

    def name_display(self, obj):
        return obj.name
    name_display.short_description = "성명(대상자)"

    def ssn_display(self, obj):
        return obj.ssn
    ssn_display.short_description = "주민번호(대상자)"

    def postcode_display(self, obj):
        return obj.postcode
    postcode_display.short_description = "우편번호(대상자)"

    def address_display(self, obj):
        return obj.address
    address_display.short_description = "주소(대상자)"

    def address_detail_display(self, obj):
        return obj.address_detail
    address_detail_display.short_description = "상세주소(대상자)"

    def phone_display(self, obj):
        return obj.phone
    phone_display.short_description = "전화번호(대상자)"

    def email_display(self, obj):
        return obj.email
    email_display.short_description = "이메일(대상자)"

    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = "출력일시"

    # ✅ 엑셀 export 액션
    def export_selected_joininfo_to_excel(self, request, queryset):
        return export_joininfo_as_excel(queryset, filename="selected_joininfo.xlsx")
    export_selected_joininfo_to_excel.short_description = "Download selected join info to excel"

    def export_all_joininfo_view(self, request):
        joininfo = self.model.objects.all()
        return export_joininfo_as_excel(joininfo, filename="all_joininfo.xlsx")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export-all/',
                self.admin_site.admin_view(self.export_all_joininfo_view),
                name='export_all_joininfo_excel',
            ),
        ]
        return custom_urls + urls
