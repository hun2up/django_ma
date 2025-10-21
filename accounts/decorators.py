# accounts/decorators.py
from functools import wraps
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def grade_required(allowed_grades):
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.grade in allowed_grades:
                return view_func(request, *args, **kwargs)
            return render(request, "no_permission_popup.html")
        return _wrapped_view
    return decorator
