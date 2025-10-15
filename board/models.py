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
    created_at = models.DateTimeField(auto_now_add=True)