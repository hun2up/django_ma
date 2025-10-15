# join/models.py
from django.db import models

class JoinInfo(models.Model):
    name = models.CharField(max_length=50)
    ssn = models.CharField("주민번호", max_length=14)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    
    postcode = models.CharField(max_length=10, null=True, blank=True)
    address = models.CharField(max_length=200)  # 도로명 주소
    address_detail = models.CharField(max_length=100, blank=True, null=True)  # 상세 주소

    user_id = models.CharField("사번", max_length=30, blank=True, null=True)
    user_name = models.CharField("성명", max_length=50, blank=True, null=True)
    user_branch = models.CharField("소속", max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name