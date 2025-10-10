from django.contrib import admin
from .models import JoinInfo

@admin.register(JoinInfo)
class JoinInfoAdmin(admin.ModelAdmin):
    # 리스트 페이지에 표시할 컬럼
    list_display = (
        'id', 'name', 'ssn', 'postcode', 'address', 'address_detail', 'phone', 'email', 'created_at'
    )

    # 검색 기능
    search_fields = ('name', 'email', 'phone')

    # 필터 기능
    list_filter = ('created_at',)

    # 정렬 기준
    ordering = ('-created_at',)

    # 수정 화면에서 보여줄 필드 순서
    fields = (
        'name', 'ssn', 'postcode', 'address', 'address_detail', 'phone', 'email'
    )
