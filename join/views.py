# join/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import JoinInfo
from .forms import JoinForm
from django.http import JsonResponse
from django.db import connection

def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'join/success.html')
    else:
        form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})

def db_test_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        return JsonResponse({"db_connection": "ok", "result": row[0]})
    except Exception as e:
        return JsonResponse({"db_connection": "error", "message": str(e)})
