from django import forms
from .models import Post, Comment, Task, TaskComment


# =========================================================
# Category Choices
# =========================================================
POST_CATEGORY_CHOICES = [
    ("", "선택"),
    ("위해촉", "위해촉"),
    ("리스크/유지율", "리스크/유지율"),
    ("수수료/채권", "수수료/채권"),
    ("운영자금", "운영자금"),
    ("전산", "전산"),
    ("기타", "기타"),
]

TASK_EXTRA_CATEGORY_CHOICES = [
    ("민원", "민원"),
    ("신규제휴", "신규제휴"),
]


def _merge_category_choices(base_choices, extra_choices):
    """
    base_choices 뒤에 extra_choices를 value 기준으로 중복 없이 병합
    """
    merged = list(base_choices or [])
    exist = {v for v, _ in merged}
    for v, label in (extra_choices or []):
        if v not in exist:
            merged.append((v, label))
            exist.add(v)
    return merged


# =========================================================
# Base Form: category/title/content 공통 UI
# =========================================================
class _BaseCategoryTitleContentForm(forms.ModelForm):
    """
    Post/Task 공통 폼 패턴
    - category optional
    - category가 '선택'/'빈값'이면 ""로 정규화
    """

    category_choices = POST_CATEGORY_CHOICES

    class Meta:
        fields = ["category", "title", "content"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "제목을 입력하세요"}),
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

        f = self.fields.get("category")
        if not f:
            return

        f.required = False
        choices = list(self.category_choices or [])
        f.choices = choices

        # widget이 Select가 아니거나 choices 누락되는 케이스 방어
        if not isinstance(f.widget, forms.Select):
            f.widget = forms.Select(attrs={"class": "form-select"})
        f.widget.choices = choices

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("category") in (None, "", "선택"):
            cleaned["category"] = ""
        return cleaned


class PostForm(_BaseCategoryTitleContentForm):
    """
    ✅ 업무요청(Post): 기본 항목 유지
    """
    category_choices = POST_CATEGORY_CHOICES

    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Post


class TaskForm(_BaseCategoryTitleContentForm):
    """
    ✅ 직원업무(Task): Post 구분 + 추가 구분(민원/신규제휴)
    """
    category_choices = _merge_category_choices(POST_CATEGORY_CHOICES, TASK_EXTRA_CATEGORY_CHOICES)

    class Meta(_BaseCategoryTitleContentForm.Meta):
        model = Task


# =========================================================
# Comment Forms
# =========================================================
class _BaseCommentForm(forms.ModelForm):
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
