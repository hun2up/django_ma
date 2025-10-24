# django_ma/partner/views.py
from django.shortcuts import render, redirect

# ✅ 기본 수수료 페이지 접속 시 → 채권관리 페이지로 자동 이동
def redirect_to_calculate(request):
    return redirect('manage_calculate')

# Create your views here.
# ✅ 권한관리 (제작중)
def manage_grades(request):
    return render(request, 'partner/manage_grades.html')

# ✅ 편제변경 (제작중)
def manage_charts(request):
    return render(request, 'partner/manage_charts.html')

# ✅ 지점효율 (제작중)
def manage_calculate(request):
    return render(request, 'partner/manage_calculate.html')