from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Post(models.Model):
    category = models.CharField(max_length=7)
    insu = models.CharField(max_length=4)
    serial = models.CharField(max_length=20)
    fa = models.CharField(max_length=20)
    code = models.IntegerField(validators=[MinValueValidator(1600000), MaxValueValidator(3000000)])
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
