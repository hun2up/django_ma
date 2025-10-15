# django_ma/board/forms.py
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['category', 'fa', 'code', 'title', 'content']
        widgets = {
            'category': forms.Select(
                choices=[
                    ('', '선택'),
                    ('위해촉', '위해촉'),
                    ('리스크/유지율', '리스크/유지율'),
                    ('수수료/채권', '수수료/채권'),
                    ('운영자금', '운영자금'),
                    ('전산', '전산'),
                    ('기타', '기타')
                ],
                attrs={'class': 'form-select'}
            ),
            'fa': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.NumberInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '제목을 입력하세요'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': (
            '요청 내용을 구체적으로 작성해주세요.\n\n'
            '개별 계약 건별 요청인 경우\n'
            '증권번호 및 보험사 전산화면 캡처본(촬영본)을 첨부해주시면\n'
            '더 빠르고 정확하게 안내드릴 수 있습니다.')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['category', 'fa', 'code']:
            self.fields[field].required = False  # 선택 항목 설정

    def clean(self):
        cleaned_data = super().clean()
        for field in ['category', 'fa']:
            if cleaned_data.get(field) in [None, '', '선택']:
                cleaned_data[field] = ''
        return cleaned_data