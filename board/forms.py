# django_ma/board/forms.py

from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        # ✅ 대상자 입력 제거
        fields = ["category", "title", "content"]
        widgets = {
            "category": forms.Select(
                choices=[
                    ("", "선택"),
                    ("위해촉", "위해촉"),
                    ("리스크/유지율", "리스크/유지율"),
                    ("수수료/채권", "수수료/채권"),
                    ("운영자금", "운영자금"),
                    ("전산", "전산"),
                    ("기타", "기타"),
                ],
                attrs={"class": "form-select"},
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "제목을 입력하세요"}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "요청 내용을 구체적으로 작성해주세요.\n\n"
                        "개별 계약 건별 요청인 경우\n"
                        "증권번호 및 보험사 전산화면 캡처본(촬영본)을 첨부해주시면\n"
                        "더 빠르고 정확하게 안내드릴 수 있습니다."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ 지금 폼에 존재하는 필드만 required=False 처리
        for field in ("category",):
            if field in self.fields:
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        # ✅ category '선택'/'None' 등을 빈값 처리
        if cleaned_data.get("category") in (None, "", "선택"):
            cleaned_data["category"] = ""
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 1,
                    "placeholder": "댓글을 입력하세요...",
                    "class": "form-control-sm",
                    "style": "resize:none; min-height:38px; font-size:14px; line-height:1.4;",
                }
            ),
        }
