# django_ma/manual/forms.py

from __future__ import annotations

from django import forms

from .constants import MANUAL_TITLE_MAX_LEN
from .models import Manual


class ManualForm(forms.ModelForm):
    """
    ✅ 매뉴얼 기본 폼
    - content는 Quill이 hidden input/textarea에 채우는 구조를 가정
    """

    class Meta:
        model = Manual
        fields = ["title", "content", "admin_only", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": MANUAL_TITLE_MAX_LEN}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean_title(self) -> str:
        title = (self.cleaned_data.get("title") or "").strip()
        if not title:
            raise forms.ValidationError("제목은 필수입니다.")
        return title
