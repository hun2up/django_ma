# django_ma/dash/models.py
from django.db import models
from django.conf import settings

class SalesRecord(models.Model):
    """
    업로드 엑셀의 '증권번호'를 PK로 사용하여 매월 파일이 재업로드 되어도 upsert 가능하도록 설계.
    """

    LIFE_NL_CHOICES = [
        ('손보', '손보'),
        ('생보', '생보'),
        ('기타', '기타'),
    ]

    # ✅ 고유값(PK)
    policy_no = models.CharField("증권번호", max_length=60, primary_key=True)

    # ✅ 사용자(설계사) 연결
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales_records',
        db_index=True,
        verbose_name="설계사"
    )

    # (스냅샷) 업로드 당시의 소속/지점도 같이 저장(사용자 정보가 변경되더라도 당시 기록 유지)
    part_snapshot = models.CharField("부서(스냅샷)", max_length=30, blank=True, null=True)
    branch_snapshot = models.CharField("지점(스냅샷)", max_length=100, blank=True, null=True)
    name_snapshot = models.CharField("성명(스냅샷)", max_length=100, blank=True, null=True)
    emp_id_snapshot = models.CharField("사원번호(스냅샷)", max_length=30, blank=True, null=True)

    # ✅ 신규 컬럼들
    insurer = models.CharField("보험사", max_length=60, db_index=True)
    contractor = models.CharField("계약자", max_length=100, blank=True, null=True)
    main_premium = models.CharField("주피", max_length=50, blank=True, null=True)  # 엑셀에서 값이 숫자/문자 혼재 가능해 문자열 권장

    ins_start = models.DateField("보험시작", blank=True, null=True)
    ins_end = models.DateField("보험종기", blank=True, null=True)

    pay_method = models.CharField("납입방법", max_length=30, blank=True, null=True)

    receipt_date = models.DateField("영수일자", blank=True, null=True, db_index=True)
    receipt_amount = models.BigIntegerField("영수금", blank=True, null=True)

    product_code = models.CharField("보험사 상품코드", max_length=60, blank=True, null=True)
    product_name = models.CharField("보험사 상품명", max_length=255, blank=True, null=True)

    # ✅ [손생] 추가
    life_nl = models.CharField("손생", max_length=10, choices=LIFE_NL_CHOICES, default='기타', db_index=True)

    # ✅ 업로드/집계용 (대시보드 월도)
    ym = models.CharField("월도(YYYY-MM)", max_length=7, db_index=True)

    updated_at = models.DateTimeField("업데이트", auto_now=True)
    created_at = models.DateTimeField("생성", auto_now_add=True)

    class Meta:
        db_table = "dash_sales_record"
        verbose_name = "매출레코드"
        verbose_name_plural = "매출레코드"
        indexes = [
            models.Index(fields=['ym', 'insurer']),
            models.Index(fields=['ym', 'life_nl']),
            models.Index(fields=['ym', 'user']),
        ]

    def __str__(self):
        return f"{self.policy_no} / {self.insurer} / {self.ym}"
