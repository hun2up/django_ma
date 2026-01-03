# django_ma/commission/models.py

from django.db import models
from django.conf import settings
from decimal import Decimal


class DepositSummary(models.Model):
    """
    deposit_summary
    - 사번(user) 1명당 1행(요약 지표)
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="deposit_summary",
        verbose_name="사번",
    )

    DIV_CHOICES = (
        ("정상", "정상"),
        ("분급", "분급"),
    )    

    # 주요지표
    final_payment = models.BigIntegerField(default=0, verbose_name="최종지급액")
    sales_total = models.BigIntegerField(default=0, verbose_name="장기총실적")
    refund_expected = models.BigIntegerField(default=0, verbose_name="환수예상")
    pay_expected = models.BigIntegerField(default=0, verbose_name="지급예상")
    maint_total = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"), verbose_name="손생합산통산")

    # 보증/기타/채권
    debt_total = models.BigIntegerField(default=0, verbose_name="채권합계")
    surety_total = models.BigIntegerField(default=0, verbose_name="보증합계")
    other_total = models.BigIntegerField(default=0, verbose_name="기타합계")
    required_debt = models.BigIntegerField(default=0, verbose_name="필요채권")
    final_excess_amount = models.BigIntegerField(default=0, verbose_name="최종초과금액")

    # 기타지표
    div_1m = models.CharField(max_length=10, blank=True, default="", choices=DIV_CHOICES, verbose_name="1개월전분급")
    div_2m = models.CharField(max_length=10, blank=True, default="", choices=DIV_CHOICES, verbose_name="2개월전분급")
    div_3m = models.CharField(max_length=10, blank=True, default="", choices=DIV_CHOICES, verbose_name="3개월전분급")
    inst_current = models.BigIntegerField(default=0, verbose_name="당월인정계속분")
    inst_prev = models.BigIntegerField(default=0, verbose_name="전월인정계속분")

    # 수수료현황
    refund_ns = models.BigIntegerField(default=0, verbose_name="환수손보")
    refund_ls = models.BigIntegerField(default=0, verbose_name="환수생보")
    pay_ns = models.BigIntegerField(default=0, verbose_name="지급손보")
    pay_ls = models.BigIntegerField(default=0, verbose_name="지급생보")

    comm_3m = models.BigIntegerField(default=0, verbose_name="3개월총수수료")
    comm_6m = models.BigIntegerField(default=0, verbose_name="6개월총수수료")
    comm_9m = models.BigIntegerField(default=0, verbose_name="9개월총수수료")
    comm_12m = models.BigIntegerField(default=0, verbose_name="12개월총수수료")

    # 유지율/수금율 (요청 그대로 표기했지만, 필드명은 안전하게)
    # 회차유지율
    ns_13_round = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="13회손보회차")
    ns_18_round = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회손보회차")
    ls_13_round = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="13회생보회차")
    ls_18_round = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회생보회차")
    
    # 통산유지율
    ns_18_total = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회손보통산")
    ns_25_total = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="25회손보통산")
    ls_18_total = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회생보통산")
    ls_25_total = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="25회생보통산")

    # 응당수금율
    ns_2_6_due = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-6회손보응당")
    ns_2_13_due = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-13회손보응당")
    ls_2_6_due = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-6회생보응당")
    ls_2_13_due = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-13회생보응당")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deposit_summary"
        verbose_name = "채권 요약"
        verbose_name_plural = "채권 요약"


class DepositSurety(models.Model):
    """
    deposit_surety
    - 보증보험 상세
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deposit_sureties",
        verbose_name="사번",
    )
    product_name = models.CharField(max_length=200, verbose_name="상품명")
    policy_no = models.CharField(max_length=100, blank=True, default="", verbose_name="증권번호")
    amount = models.BigIntegerField(default=0, verbose_name="가입금액")
    status = models.CharField(max_length=50, blank=True, default="", verbose_name="상태")
    start_date = models.DateField(null=True, blank=True, verbose_name="보험가입일")
    end_date = models.DateField(null=True, blank=True, verbose_name="보험종료일")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deposit_surety"
        verbose_name = "보증보험"
        verbose_name_plural = "보증보험"


class DepositOther(models.Model):
    """
    deposit_others
    - 기타채권 상세
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deposit_others",
        verbose_name="사번",
    )
    product_name = models.CharField(max_length=200, verbose_name="상품명")
    product_type = models.CharField(max_length=200, blank=True, default="", verbose_name="보증내용")
    amount = models.BigIntegerField(default=0, verbose_name="가입금액")
    bond_no = models.CharField(max_length=100, blank=True, default="", verbose_name="채권번호")
    status = models.CharField(max_length=50, blank=True, default="", verbose_name="상태")
    start_date = models.DateField(null=True, blank=True, verbose_name="가입일")
    memo = models.CharField(max_length=255, blank=True, default="", verbose_name="비고")    

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deposit_others"
        verbose_name = "기타채권"
        verbose_name_plural = "기타채권"


class DepositUploadLog(models.Model):
    """
    ✅ 부서(part)별 + 업로드 구분별 "마지막 업로드 일자" 표시용
    """
    part = models.CharField(max_length=50, db_index=True, verbose_name="부서")
    upload_type = models.CharField(max_length=50, db_index=True, verbose_name="업로드 구분")
    uploaded_at = models.DateTimeField(auto_now=True, verbose_name="마지막 업로드 일시")
    row_count = models.IntegerField(default=0, verbose_name="반영 건수")
    file_name = models.CharField(max_length=255, blank=True, default="", verbose_name="파일명")

    class Meta:
        db_table = "deposit_upload_log"
        unique_together = ("part", "upload_type")
        verbose_name = "채권 업로드 로그"
        verbose_name_plural = "채권 업로드 로그"
