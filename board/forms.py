# django_ma/board/forms.py

from django import forms
from .models import Post, Comment, Task, TaskComment


# ✅ 업무요청(Post) 기본 구분(기존 유지)
POST_CATEGORY_CHOICES = [
    ("", "선택"),
    ("위해촉", "위해촉"),
    ("리스크/유지율", "리스크/유지율"),
    ("수수료/채권", "수수료/채권"),
    ("운영자금", "운영자금"),
    ("전산", "전산"),
    ("기타", "기타"),
]

# ✅ 직원업무(Task)에서만 추가할 구분
TASK_EXTRA_CATEGORY_CHOICES = [
    ("민원", "민원"),
    ("신규제휴", "신규제휴"),
]


def _merge_category_choices(base_choices, extra_choices):
    """
    base_choices 뒤에 extra_choices를 중복 없이 붙임(value 기준).
    base 순서는 유지, extra는 뒤에 추가.
    """
    merged = list(base_choices or [])
    exist = {v for v, _ in merged}
    for v, label in (extra_choices or []):
        if v not in exist:
            merged.append((v, label))
            exist.add(v)
    return merged


class _BaseCategoryTitleContentForm(forms.ModelForm):
    """
    Post/Task 공통 폼 패턴
    - fields: category, title, content
    - category는 선택(optional)
    - category '선택'은 빈값으로 정규화
    """

    # ✅ 기본값(자식 폼에서 override)
    category_choices = POST_CATEGORY_CHOICES

    class Meta:
        fields = ["category", "title", "content"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
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

        if "category" in self.fields:
            f = self.fields["category"]
            f.required = False

            # ✅ 핵심: field.choices + widget.choices 둘 다 강제 세팅
            choices = list(self.category_choices or [])
            f.choices = choices
            if getattr(f, "widget", None):
                f.widget.choices = choices

            # ✅ 혹시 widget이 Select가 아닌 경우도 대비(안전)
            if not isinstance(f.widget, forms.Select):
                f.widget = forms.Select(attrs={"class": "form-select"})
                f.widget.choices = choices

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("category") in (None, "", "선택"):
            cleaned_data["category"] = ""
        return cleaned_data


class PostForm(_BaseCategoryTitleContentForm):
    """
    ✅ 업무요청(Post): 기존 항목 유지
    """
    category_choices = POST_CATEGORY_CHOICES

    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Post


class TaskForm(_BaseCategoryTitleContentForm):
    """
    ✅ 직원업무(Task): 기존 + 민원/신규제휴 추가
    """
    category_choices = _merge_category_choices(POST_CATEGORY_CHOICES, TASK_EXTRA_CATEGORY_CHOICES)

    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Task


class _BaseCommentForm(forms.ModelForm):
    """
    Comment / TaskComment 공통 UI
    """
    class Meta:
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


class CommentForm(_BaseCommentForm):
    class Meta(_BaseCommentForm.Meta):
        model = Comment


class TaskCommentForm(_BaseCommentForm):
    class Meta(_BaseCommentForm.Meta):
        model = TaskComment
