# django_ma/board/forms.py

from django import forms
from .models import Post, Comment, Task, TaskComment


CATEGORY_CHOICES = [
    ("", "선택"),
    ("위해촉", "위해촉"),
    ("리스크/유지율", "리스크/유지율"),
    ("수수료/채권", "수수료/채권"),
    ("운영자금", "운영자금"),
    ("전산", "전산"),
    ("기타", "기타"),
]


class _BaseCategoryTitleContentForm(forms.ModelForm):
    """
    Post/Task 공통 폼 패턴
    - fields: category, title, content
    - category는 선택(optional)
    - category '선택'은 빈값으로 정규화
    """
    class Meta:
        fields = ["category", "title", "content"]
        widgets = {
            "category": forms.Select(
                choices=CATEGORY_CHOICES,
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
        # category는 선택값
        if "category" in self.fields:
            self.fields["category"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("category") in (None, "", "선택"):
            cleaned_data["category"] = ""
        return cleaned_data


class PostForm(_BaseCategoryTitleContentForm):
    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Post


class TaskForm(_BaseCategoryTitleContentForm):
    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Task


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


class TaskCommentForm(forms.ModelForm):
    """
    TaskComment는 post의 Comment와 모델이 다르므로 분리하는 게 정석.
    (task_detail에서 CommentForm 재사용하던 부분까지 깔끔해짐)
    """
    class Meta:
        model = TaskComment
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
