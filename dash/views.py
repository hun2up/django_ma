from django.shortcuts import render, redirect

# ✅ 기본 수수료 페이지 접속 시 → 채권관리 페이지로 자동 이동
def redirect_to_sales(request):
    return redirect('dash_sales')

# Create your views here.
# ✅ 매출현황 대시보드 (제작중)
def dash_sales(request):
    return render(request, 'dash/dash_sales.html')

# ✅ 리쿠르팅 대시보드 (제작중)
def dash_recruit(request):
    return render(request, 'dash/dash_recruit.html')

# ✅ 유지율 대시보드 (제작중)
def dash_retention(request):
    return render(request, 'dash/dash_retention.html')