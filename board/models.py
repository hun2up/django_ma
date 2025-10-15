# django_ma/board/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Post(models.Model):
    receipt_number = models.CharField(max_length=20, unique=True, blank=True)
    
    category = models.CharField(max_length=7, default="", blank=True)
    fa = models.CharField(max_length=20, default="", blank=True)
    
    code = models.IntegerField(
        validators=[MinValueValidator(1600000), MaxValueValidator(3000000)],
        blank=True, null=True
    )

    title = models.CharField(max_length=200)
    content = models.TextField()

    user_id = models.CharField(max_length=30, blank=True)       # 사번
    user_name = models.CharField(max_length=100, blank=True)    # 성명
    user_branch = models.CharField(max_length=100, blank=True)  # 소속

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            today = timezone.localtime().date()
            today_str = today.strftime('%Y%m%d')
            
            # 오늘 날짜의 게시물 수 + 1 → 세자리 순번
            count_today = Post.objects.filter(created_at__date=today).count() + 1
            self.receipt_number = f"{today_str}{count_today:03d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.receipt_number}] {self.title}"

    class Meta:
        ordering = ['-created_at']
