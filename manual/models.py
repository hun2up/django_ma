# django_ma/manual/models.py
from django.db import models
from django.conf import settings

class Manual(models.Model):
    title = models.CharField(max_length=80)
    content = models.TextField(blank=True)
    admin_only = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    # ✅ 추가: 정렬 순서
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-updated_at"]  # ✅ 기본 정렬


class ManualBlock(models.Model):
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, related_name="blocks")
    content = models.TextField(blank=True)  # HTML 저장
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
