# django_ma/partner/models.py
from django.db import models
from accounts.models import CustomUser


class StructureChange(models.Model):
    """편제변경 메인 데이터 (메인시트)"""
    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='structure_requests')
    target = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='structure_targets')
    branch = models.CharField(max_length=50, blank=True, null=True)  # 요청자 소속
    target_branch = models.CharField(max_length=50, blank=True, null=True)
    chg_branch = models.CharField(max_length=50, blank=True, null=True)
    or_flag = models.BooleanField(default=False)
    rank = models.CharField(max_length=20, blank=True, null=True)
    chg_rank = models.CharField(max_length=20, blank=True, null=True)
    table_name = models.CharField(max_length=20, blank=True, null=True)
    chg_table = models.CharField(max_length=20, blank=True, null=True)
    rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    chg_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    memo = models.CharField(max_length=100, blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    process_date = models.DateTimeField(blank=True, null=True)
    month = models.CharField(max_length=7, help_text="YYYY-MM")

    def __str__(self):
        return f"{self.month} - {self.target.name if self.target else '-'}"


class PartnerChangeLog(models.Model):
    """편제변경 로그"""
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)  # 'save' / 'delete' / 'set_deadline'
    detail = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} - {self.action}"


class StructureDeadline(models.Model):
    branch = models.CharField(max_length=50)
    month = models.CharField(max_length=7)  # YYYY-MM
    deadline_day = models.PositiveSmallIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "month")

    def __str__(self):
        return f"{self.branch} {self.month} ({self.deadline_day}일)"