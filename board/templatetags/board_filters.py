import os
from django import template

register = template.Library()

print("✅ custom_filters.py 로드됨")  # 서버 실행 시 출력됨

@register.filter
def basename(value):
    print(f"📦 basename 필터 호출됨 - 값: {value}")  # 템플릿에서 사용될 때 출력됨
    return os.path.basename(value)

print("✅ custom_filters.py 로드됨")