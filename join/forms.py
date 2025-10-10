# join/forms.py
from django import forms
from .models import JoinInfo

class JoinForm(forms.ModelForm):
    email = forms.EmailField(required=False)  # ✅ 필수 아님으로 명시
    
    class Meta:
        model = JoinInfo
        fields = ['name', 'ssn', 'address', 'phone', 'email']
