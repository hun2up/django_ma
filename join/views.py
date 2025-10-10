# join/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import JoinInfo
from .forms import JoinForm
from django.http import JsonResponse
from django.db import connection

def db_test_view(request):
    return HttpResponse("DB 테스트 뷰입니다.")

def join_form(request):
    if request.method == 'POST':
        JoinInfo.objects.create(
            name=request.POST.get("name"),
            ssn=request.POST.get("ssn"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            postcode=request.POST.get("postcode"),
            address=request.POST.get("address"),
            address_detail=request.POST.get("address_detail", "")
        )
        return render(request, 'join/success.html')
    return render(request, 'join/join_form.html')
