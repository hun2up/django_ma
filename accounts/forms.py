# django_ma/accounts/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


# =============================================================================
# Excel Upload Form
# =============================================================================

class ExcelUploadForm(forms.Form):
    """
    Excel 업로드 공용 폼 (.xlsx)
    """
    file = forms.FileField(label="Select an Excel file (.xlsx)")


# =============================================================================
# Login Form (활성 사용자만 로그인 허용)
# =============================================================================

class ActiveOnlyAuthenticationForm(AuthenticationForm):
    """
    비활성화(is_active=False) 계정 로그인 차단
    """
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not getattr(user, "is_active", True):
            raise ValidationError("비활성화된 계정입니다.", code="inactive")
