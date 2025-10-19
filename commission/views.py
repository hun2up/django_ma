# django_ma/commission/views.py
from django.shortcuts import render, redirect
from accounts.decorators import grade_required

# ✅ 기본 수수료 페이지 접속 시 → 채권관리 페이지로 자동 이동
@grade_required(['superuser'])
def redirect_to_deposit(request):
    return redirect('deposit_home')

# ✅ 채권관리 페이지 (메인)
@grade_required(['superuser'])
def deposit_home(request):
    return render(request, 'commission/deposit_home.html')

# ✅ 지원신청서 (제작중)
@grade_required(['superuser'])
def support_home(request):
    return render(request, 'commission/support_home.html')

# ✅ 수수료결재 (제작중)
@grade_required(['superuser'])
def approval_home(request):
    return render(request, 'commission/approval_home.html')