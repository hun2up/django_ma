# join/forms.py
from django import forms
from .models import JoinInfo

class JoinForm(forms.ModelForm):
    email = forms.EmailField(required=False)  # 선택항목
    class Meta:
        model = JoinInfo
        fields = ['name', 'ssn', 'phone', 'email', 'postcode', 'address', 'address_detail']
