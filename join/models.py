# join/models.py
from django.db import models

class JoinInfo(models.Model):
    name = models.CharField(max_length=50)
    ssn = models.CharField("주민번호", max_length=14)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"
