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


def not_inactive_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        # inactive만 차단, 나머지는 통과
        if getattr(request.user, "grade", None) == "inactive":
            return render(request, "no_permission_popup.html")
        return view_func(request, *args, **kwargs)
    return _wrapped