# board/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Post(models.Model):
    category = models.CharField(max_length=7, blank=True, null=True, default="")
    fa = models.CharField(max_length=20, blank=True, null=True, default="")
    code = models.IntegerField(
        validators=[MinValueValidator(1600000), MaxValueValidator(3000000)],
        blank=True, null=True
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    user_id = models.CharField(max_length=30, blank=True, null=True)       # 사번
    user_name = models.CharField(max_length=100, blank=True, null=True)    # 성명
    user_branch = models.CharField(max_length=100, blank=True, null=True)  # 소속
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title