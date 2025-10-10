# join/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import JoinInfo
from .forms import JoinForm

def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'join/success.html')
    else:
        form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})
