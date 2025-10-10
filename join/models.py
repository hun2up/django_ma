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

    created_at = models.DateTimeField(auto_now_add=True)
