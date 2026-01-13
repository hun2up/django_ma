from decimal import Decimal

from django.conf import settings
from django.db import models


# ============================================================================
# 1) 채권(Deposit) - 요약/상세 모델
#    - DepositSummary : 사번 1명당 1행(요약 지표)
#    - DepositSurety  : 보증보험 상세
#    - DepositOther   : 기타채권 상세
#    - DepositUploadLog : 부서/업로드구분별 마지막 업로드 기록
# ============================================================================

class DepositSummary(models.Model):
    """
    deposit_summary
    - 사번(user) 1명당 1행(요약 지표)
    - 화면: /commission/deposit/ (채권현황)
    """

    # -----------------------------
    # Choices / Constants
    # -----------------------------
    DIV_CHOICES = (
        ("정상", "정상"),
        ("분급", "분급"),
    )

    # -----------------------------
    # PK / Relation
    # -----------------------------
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="deposit_summary",
        verbose_name="사번",
    )

    # -----------------------------
    # 주요지표 (상단 KPI)
    # -----------------------------
    final_payment = models.BigIntegerField(default=0, verbose_name="최종지급액")
    sales_total = models.BigIntegerField(default=0, verbose_name="장기총실적")
    refund_expected = models.BigIntegerField(default=0, verbose_name="환수예상")
    pay_expected = models.BigIntegerField(default=0, verbose_name="지급예상")
    maint_total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="손생합산통산",
    )

    # -----------------------------
    # 채권 합계 (채권/보증/기타)
    # -----------------------------
    debt_total = models.BigIntegerField(default=0, verbose_name="채권합계")
    surety_total = models.BigIntegerField(default=0, verbose_name="보증합계")
    other_total = models.BigIntegerField(default=0, verbose_name="기타합계")
    required_debt = models.BigIntegerField(default=0, verbose_name="필요채권")
    final_excess_amount = models.BigIntegerField(default=0, verbose_name="최종초과금액")

    # -----------------------------
    # 기타지표 (분급/인정계속분)
    # -----------------------------
    div_1m = models.CharField(
        max_length=10,
        blank=True,
        default="",
        choices=DIV_CHOICES,
        verbose_name="1개월전분급",
    )
    div_2m = models.CharField(
        max_length=10,
        blank=True,
        default="",
        choices=DIV_CHOICES,
        verbose_name="2개월전분급",
    )
    div_3m = models.CharField(
        max_length=10,
        blank=True,
        default="",
        choices=DIV_CHOICES,
        verbose_name="3개월전분급",
    )
    inst_current = models.BigIntegerField(default=0, verbose_name="당월인정계속분")
    inst_prev = models.BigIntegerField(default=0, verbose_name="전월인정계속분")

    # -----------------------------
    # 수수료현황 (환수/지급, 손/생)
    # -----------------------------
    refund_ns = models.BigIntegerField(default=0, verbose_name="환수손보")
    refund_ls = models.BigIntegerField(default=0, verbose_name="환수생보")
    pay_ns = models.BigIntegerField(default=0, verbose_name="지급손보")
    pay_ls = models.BigIntegerField(default=0, verbose_name="지급생보")

    # -----------------------------
    # 보증(O/X) 환수/지급 상세 합계
    # - 템플릿/JS에서 data-bind로 개별 표시
    # -----------------------------
    # 보증(O) 환수
    surety_o_refund_ns = models.BigIntegerField(default=0, verbose_name="보증(O) 환수손보")
    surety_o_refund_ls = models.BigIntegerField(default=0, verbose_name="보증(O) 환수생보")
    surety_o_refund_total = models.BigIntegerField(default=0, verbose_name="보증(O) 환수합계")

    # 보증(X) 환수
    surety_x_refund_ns = models.BigIntegerField(default=0, verbose_name="보증(X) 환수손보")
    surety_x_refund_ls = models.BigIntegerField(default=0, verbose_name="보증(X) 환수생보")
    surety_x_refund_total = models.BigIntegerField(default=0, verbose_name="보증(X) 환수합계")

    # 보증(O) 지급
    surety_o_pay_ns = models.BigIntegerField(default=0, verbose_name="보증(O) 지급손보")
    surety_o_pay_ls = models.BigIntegerField(default=0, verbose_name="보증(O) 지급생보")
    surety_o_pay_total = models.BigIntegerField(default=0, verbose_name="보증(O) 지급합계")

    # 보증(X) 지급
    surety_x_pay_ns = models.BigIntegerField(default=0, verbose_name="보증(X) 지급손보")
    surety_x_pay_ls = models.BigIntegerField(default=0, verbose_name="보증(X) 지급생보")
    surety_x_pay_total = models.BigIntegerField(default=0, verbose_name="보증(X) 지급합계")

    # -----------------------------
    # 기간별 총수수료
    # -----------------------------
    comm_3m = models.BigIntegerField(default=0, verbose_name="3개월총수수료")
    comm_6m = models.BigIntegerField(default=0, verbose_name="6개월총수수료")
    comm_9m = models.BigIntegerField(default=0, verbose_name="9개월총수수료")
    comm_12m = models.BigIntegerField(default=0, verbose_name="12개월총수수료")

    # -----------------------------
    # 유지율/수금율
    # - 회차유지율 / 통산유지율 / 응당수금율
    # -----------------------------
    # 회차유지율
    ns_13_round = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="13회손보회차"
    )
    ns_18_round = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회손보회차"
    )
    ls_13_round = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="13회생보회차"
    )
    ls_18_round = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회생보회차"
    )

    # 통산유지율
    ns_18_total = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회손보통산"
    )
    ns_25_total = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="25회손보통산"
    )
    ls_18_total = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="18회생보통산"
    )
    ls_25_total = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="25회생보통산"
    )

    # 응당수금율
    ns_2_6_due = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-6회손보응당"
    )
    ns_2_13_due = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-13회손보응당"
    )
    ls_2_6_due = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-6회생보응당"
    )
    ls_2_13_due = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="2-13회생보응당"
    )

    # -----------------------------
    # Timestamp
    # -----------------------------
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deposit_summary"
        verbose_name = "채권 요약"
        verbose_name_plural = "채권 요약"

    def __str__(self):
        return f"DepositSummary({self.user_id})"


class DepositSurety(models.Model):
    """
    deposit_surety
    - 보증보험 상세
    - 화면: 채권현황(보증보험) 테이블
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deposit_sureties",
        verbose_name="사번",
    )

    # 보증보험 정보
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

    def __str__(self):
        return f"DepositSurety({self.user_id}, {self.product_name})"


class DepositOther(models.Model):
    """
    deposit_others
    - 기타채권 상세
    - 화면: 채권현황(기타채권) 테이블
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deposit_others",
        verbose_name="사번",
    )

    # 기타채권 정보
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

    def __str__(self):
        return f"DepositOther({self.user_id}, {self.product_name})"


class DepositUploadLog(models.Model):
    """
    deposit_upload_log
    - 부서(part)별 + 업로드 구분(upload_type)별 "마지막 업로드 일자" 표시용
    - 화면: /commission/deposit/ 의 '데이터 업데이트' 카드
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

    def __str__(self):
        return f"{self.part}/{self.upload_type} ({self.uploaded_at:%Y-%m-%d %H:%M})"


# ============================================================================
# 2) 결재/효율 업로드 로그 + 미결 현황
#    - ApprovalExcelUploadLog : 월도+kind별 업로드 파일 로그
#    - CommissionApprovalPending : (레거시/이전) 미결현황
#    - ApprovalPending : (현재) 미결현황(kind=approval)
# ============================================================================

class ApprovalExcelUploadLog(models.Model):
    """
    approval_excel_upload_log
    - 결재/효율 엑셀 업로드 로그(월도+kind 단위)
    """

    KIND_CHOICES = (
        ("efficiency", "지점효율"),
        ("approval", "수수료결재"),
    )

    ym = models.CharField(max_length=7, db_index=True, verbose_name="월도(YYYY-MM)")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True, verbose_name="구분")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_excel_upload_logs",
        verbose_name="업로드 사용자",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="업로드 일시")
    row_count = models.IntegerField(default=0, verbose_name="행 수(추정)")
    file_name = models.CharField(max_length=255, blank=True, default="", verbose_name="파일명")

    class Meta:
        db_table = "approval_excel_upload_log"
        verbose_name = "결재/효율 엑셀 업로드 로그"
        verbose_name_plural = "결재/효율 엑셀 업로드 로그"
        ordering = ["-uploaded_at"]
        unique_together = ("ym", "kind")  # 월도+구분별 “마지막 업로드” 1개 유지

    def __str__(self):
        return f"{self.ym} / {self.kind} / {self.file_name}"


class CommissionApprovalPending(models.Model):
    """
    commission_approval_pending
    수수료 미결현황 (월도별) - 레거시/이전 테이블
    - 업로드 엑셀에서 사번 기준으로 users(CustomUser) 매칭
    - part/branch/name/regist 는 user에서 조인으로 표시(중복 저장 최소화)
    """

    ym = models.CharField(max_length=7, db_index=True, verbose_name="월도(YYYY-MM)")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commission_approval_pendings",
        verbose_name="사번",
    )

    emp_name = models.CharField(max_length=200, blank=True, default="", verbose_name="사원명(엑셀)")
    actual_paid = models.BigIntegerField(default=0, verbose_name="실지급액")
    approval = models.CharField(max_length=50, blank=True, default="", verbose_name="결재")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "commission_approval_pending"
        verbose_name = "수수료 미결현황"
        verbose_name_plural = "수수료 미결현황"
        ordering = ["-ym", "user_id"]
        unique_together = ("ym", "user")  # 월도+사번 1행

    def __str__(self):
        return f"{self.ym}/{self.user_id} ({self.emp_name})"


class ApprovalPending(models.Model):
    """
    approval_pending
    ✅ 수수료 미결현황 (월도별) - 현재 사용 테이블
    - 엑셀 업로드(kind=approval)로 채워짐
    """

    ym = models.CharField(max_length=7, db_index=True, verbose_name="월도(YYYY-MM)")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_pendings",
        verbose_name="사번",
    )

    emp_name = models.CharField(max_length=200, blank=True, default="", verbose_name="사원명(B열)")
    actual_pay = models.BigIntegerField(default=0, verbose_name="실지급액(N열)")
    approval_flag = models.CharField(max_length=20, blank=True, default="", verbose_name="결재(O열)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "approval_pending"
        verbose_name = "수수료 미결현황"
        verbose_name_plural = "수수료 미결현황"
        unique_together = ("ym", "user")  # 월도+사번 1행 유지
        ordering = ["ym", "user_id"]

    def __str__(self):
        return f"{self.ym}/{self.user_id} ({self.emp_name})"
