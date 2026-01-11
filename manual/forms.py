# django_ma/manual/templates/manual/forms.py

from django import forms
from .models import Manual

class ManualForm(forms.ModelForm):
    class Meta:
        model = Manual
        fields = ["title", "content", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            # content는 Quill에서 hidden으로 채울 예정이라 기본 Textarea도 OK
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
