# django_ma/commission/models.py
from django.db import models

class Payment(models.Model):
    """최종지급액 데이터"""
    user_id = models.IntegerField("사번", unique=True, db_index=True)
    amount = models.BigIntegerField("최종지급액", default=0)

    def __str__(self):
        return f"{self.user_id} - {self.amount:,}원"
