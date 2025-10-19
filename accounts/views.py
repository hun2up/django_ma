from django.shortcuts import render
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth.views import LoginView

# Create your views here.
def upload_progress_view(request):
    """업로드 진행률을 반환하는 API"""
    percent = cache.get("upload_progress", 0)
    return JsonResponse({"percent": percent})

class SessionCloseLoginView(LoginView):
    """로그인 시 세션을 브라우저 종료 시 만료로 강제"""
    def form_valid(self, form):
        response = super().form_valid(form)
        # 0 → 브라우저 닫으면 즉시 세션 만료
        self.request.session.set_expiry(0)
        return response