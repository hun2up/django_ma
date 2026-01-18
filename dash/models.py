# django_ma/dash/models.py
from django.db import models
from django.conf import settings


class SalesRecord(models.Model):
    """
    업로드 엑셀의 '증권번호'를 PK로 사용하여 매월 파일이 재업로드 되어도 upsert 가능하도록 설계.
    """

    LIFE_NL_CHOICES = [
        ("손보", "손보"),
        ("생보", "생보"),
        ("자동차", "자동차"),
    ]

    policy_no = models.CharField("증권번호", max_length=60, primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_records",
        db_index=True,
        verbose_name="설계사",
    )

    part_snapshot = models.CharField("부서(스냅샷)", max_length=30, blank=True, null=True)
    branch_snapshot = models.CharField("지점(스냅샷)", max_length=100, blank=True, null=True)
    name_snapshot = models.CharField("성명(스냅샷)", max_length=100, blank=True, null=True)
    emp_id_snapshot = models.CharField("사원번호(스냅샷)", max_length=30, blank=True, null=True)

    insurer = models.CharField("보험사", max_length=60, db_index=True)
    contractor = models.CharField("계약자", max_length=100, blank=True, null=True)

    insured = models.CharField("피보험자", max_length=100, blank=True, null=True)

    ins_start = models.DateField("보험시작", blank=True, null=True)
    ins_end = models.DateField("보험종기", blank=True, null=True)

    pay_method = models.CharField("납입방법", max_length=30, blank=True, null=True)

    receipt_date = models.DateField("영수일자", blank=True, null=True, db_index=True)
    receipt_amount = models.BigIntegerField("영수금", blank=True, null=True)

    product_code = models.CharField("상품코드", max_length=60, blank=True, null=True)
    product_name = models.CharField("상품명", max_length=255, blank=True, null=True)

    # ✅ 자동차 파일에서 사용하는 차량번호
    vehicle_no = models.CharField("차량번호", max_length=40, blank=True, null=True, db_index=True)

    # ✅ 자동차 전용
    car_liability = models.BigIntegerField("책임", blank=True, null=True)
    car_optional = models.BigIntegerField("임의", blank=True, null=True)
    status = models.CharField("상태", max_length=40, blank=True, null=True)

    life_nl = models.CharField("손생", max_length=10, choices=LIFE_NL_CHOICES, default="손보", db_index=True)

    ym = models.CharField("월도(YYYY-MM)", max_length=7, db_index=True)

    updated_at = models.DateTimeField("업데이트", auto_now=True)
    created_at = models.DateTimeField("생성", auto_now_add=True)

    class Meta:
        db_table = "dash_sales_record"
        verbose_name = "매출레코드"
        verbose_name_plural = "매출레코드"
        indexes = [
            models.Index(fields=["ym", "insurer"]),
            models.Index(fields=["ym", "life_nl"]),
            models.Index(fields=["ym", "user"]),
            models.Index(fields=["ym", "vehicle_no"]),
        ]

    def __str__(self):
        return f"{self.policy_no} / {self.insurer} / {self.ym}"
