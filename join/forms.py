# join/forms.py
from django import forms
from .models import JoinInfo

class JoinForm(forms.ModelForm):
    class Meta:
        model = JoinInfo
        fields = ['name', 'ssn', 'address', 'phone', 'email']
