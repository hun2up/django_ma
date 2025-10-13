# join/forms.py
from django import forms
from .models import JoinInfo

class JoinForm(forms.ModelForm):
    email = forms.EmailField(required=False, label='이메일 (선택)')  # 선택항목

    class Meta:
        model = JoinInfo
        fields = ['name', 'ssn', 'phone', 'email', 'postcode', 'address', 'address_detail']
        labels = {
            'name': '이름',
            'ssn': '주민번호',
            'phone': '전화번호',
            'postcode': '우편번호',
            'address': '도로명 주소',
            'address_detail': '상세주소',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'ssn': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'postcode': forms.TextInput(attrs={'class': 'form-control', 'readonly': True, 'required': True, 'id': 'postcode'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'readonly': True, 'required': True, 'id': 'address'}),
            'address_detail': forms.TextInput(attrs={'class': 'form-control', 'id': 'address_detail'}),
        }
