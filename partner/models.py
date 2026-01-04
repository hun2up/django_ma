# django_ma/partner/models.py

from django.db import models
from accounts.models import CustomUser


class RateChange(models.Model):
    requester = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="ratechange_requests")
    target = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="ratechange_targets")

    part = models.CharField(max_length=50, default="-")
    branch = models.CharField(max_length=50, default="-")
    month = models.CharField(max_length=7, db_index=True)  # "YYYY-MM"

    before_ftable = models.CharField(max_length=100, blank=True, default="")
    before_frate = models.CharField(max_length=20, blank=True, default="")
    before_ltable = models.CharField(max_length=100, blank=True, default="")
    before_lrate = models.CharField(max_length=20, blank=True, default="")

    after_ftable = models.CharField(max_length=100, blank=True, default="")
    after_frate = models.CharField(max_length=20, blank=True, default="")
    after_ltable = models.CharField(max_length=100, blank=True, default="")
    after_lrate = models.CharField(max_length=20, blank=True, default="")

    memo = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    process_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["month", "branch"])]


# ------------------------------------------------------------
# 편제 변경 (조직 관리)
# ------------------------------------------------------------
class StructureChange(models.Model):
    requester = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name="structure_requests", help_text="변경 요청자"
    )
    target = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name="structure_targets", help_text="변경 대상자"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    part = models.CharField(max_length=50, blank=True, null=True, verbose_name="부서")
    branch = models.CharField(max_length=50, blank=True, null=True, help_text="요청자 소속")
    target_branch = models.CharField(max_length=50, blank=True, null=True, help_text="대상자 기존 소속")
    chg_branch = models.CharField(max_length=50, blank=True, null=True, help_text="변경 후 소속")

    rank = models.CharField(max_length=20, blank=True, null=True)
    chg_rank = models.CharField(max_length=20, blank=True, null=True)
    table_name = models.CharField(max_length=20, blank=True, null=True)
    chg_table = models.CharField(max_length=20, blank=True, null=True)

    rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    chg_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    memo = models.CharField(max_length=100, blank=True, null=True)
    or_flag = models.BooleanField(default=False, help_text="OR 여부 플래그")

    month = models.CharField(max_length=7, help_text="YYYY-MM")
    request_date = models.DateTimeField(auto_now_add=True)
    process_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "편제변경 데이터"
        verbose_name_plural = "편제변경 데이터"
        ordering = ["-month", "-request_date"]

    def __str__(self):
        target_name = getattr(self.target, "name", "-")
        return f"{self.month} - {target_name}"


class PartnerChangeLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, help_text="작업자")
    action = models.CharField(max_length=50, help_text="수행된 작업 유형 (save/delete/set_deadline 등)")
    detail = models.TextField(blank=True, null=True, help_text="추가 상세 내역")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "편제변경 로그"
        verbose_name_plural = "편제변경 로그"
        ordering = ["-timestamp"]

    def __str__(self):
        user_name = getattr(self.user, "name", str(self.user))
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {user_name} - {self.action}"


class StructureDeadline(models.Model):
    branch = models.CharField(max_length=50)
    month = models.CharField(max_length=7, help_text="YYYY-MM")
    deadline_day = models.PositiveSmallIntegerField(help_text="마감 일자 (1~31)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "month")
        verbose_name = "편제변경 마감일"
        verbose_name_plural = "편제변경 마감일"
        ordering = ["-month", "branch"]

    def __str__(self):
        return f"{self.branch} {self.month} ({self.deadline_day}일)"


class SubAdminTemp(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="subadmin_detail")

    name = models.CharField(max_length=50)
    part = models.CharField(max_length=50, blank=True, null=True)
    branch = models.CharField(max_length=50, blank=True, null=True)
    grade = models.CharField(max_length=20, blank=True, null=True)

    team_a = models.CharField(max_length=50, blank=True, null=True)
    team_b = models.CharField(max_length=50, blank=True, null=True)
    team_c = models.CharField(max_length=50, blank=True, null=True)
    position = models.CharField(max_length=30, blank=True, null=True)

    LEVEL_CHOICES = [
        ("-", "-"),
        ("A레벨", "A레벨"),
        ("B레벨", "B레벨"),
        ("C레벨", "C레벨"),
    ]
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="-", verbose_name="레벨")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_subadmin_temp"
        verbose_name = "권한관리 확장정보"
        verbose_name_plural = "권한관리 확장정보"

    def __str__(self):
        return f"{self.name} ({self.part})"


class TableSetting(models.Model):
    branch = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    rate = models.CharField(max_length=20, blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="표시 순서")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("branch", "table_name")
        ordering = ["branch", "table_name"]

    def __str__(self):
        return f"{self.branch} - {self.table_name}"


class RateTable(models.Model):
    user = models.OneToOneField(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="rate_table",
        verbose_name="사용자",
    )

    branch = models.CharField(max_length=50, blank=True, null=True, verbose_name="지점")
    team_a = models.CharField(max_length=50, blank=True, null=True, verbose_name="팀A")
    team_b = models.CharField(max_length=50, blank=True, null=True, verbose_name="팀B")
    team_c = models.CharField(max_length=50, blank=True, null=True, verbose_name="팀C")

    non_life_table = models.CharField(max_length=100, blank=True, null=True, verbose_name="손보 테이블명")
    life_table = models.CharField(max_length=100, blank=True, null=True, verbose_name="생보 테이블명")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "요율관리 테이블"
        verbose_name_plural = "요율관리 테이블"
        ordering = ["branch", "user__name"]

    def __str__(self):
        return f"{self.user.name} ({self.branch})"


# ------------------------------------------------------------
# ✅ 지점효율 확인서 업로드 그룹
# ------------------------------------------------------------
class EfficiencyConfirmGroup(models.Model):
    confirm_group_id = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="그룹ID")

    uploader = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="efficiency_confirm_groups",
        verbose_name="업로더",
    )

    part = models.CharField(max_length=50, default="-", verbose_name="부서")
    branch = models.CharField(max_length=50, default="-", verbose_name="지점")
    month = models.CharField(max_length=7, db_index=True, verbose_name="월(YYYY-MM)")

    title = models.CharField(max_length=120, blank=True, default="", verbose_name="그룹 제목")
    note = models.CharField(max_length=200, blank=True, default="", verbose_name="메모")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["month", "branch"])]
        verbose_name = "지점효율 확인서(그룹)"
        verbose_name_plural = "지점효율 확인서(그룹)"

    def __str__(self):
        return f"{self.month}/{self.branch} [{self.confirm_group_id}]"


# ------------------------------------------------------------
# ✅ 지점효율 확인서 첨부(파일) — 방향2 핵심: group FK + related_name="attachments"
# ------------------------------------------------------------
class EfficiencyConfirmAttachment(models.Model):
    group = models.ForeignKey(
        "partner.EfficiencyConfirmGroup",
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,      # ✅ 기존 데이터 백필 위해 1단계는 null 허용
        blank=True,
        verbose_name="확인서 그룹",
    )

    uploader = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="efficiency_confirm_uploads",
        verbose_name="업로더",
    )

    part = models.CharField(max_length=50, default="-", verbose_name="부서")
    branch = models.CharField(max_length=50, default="-", verbose_name="지점")
    month = models.CharField(max_length=7, db_index=True, verbose_name="월(YYYY-MM)")

    file = models.FileField(upload_to="partner/efficiency_confirm/%Y/%m/", verbose_name="확인서 파일")
    original_name = models.CharField(max_length=255, blank=True, default="", verbose_name="원본파일명")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["month", "branch"])]
        verbose_name = "지점효율 확인서(파일)"
        verbose_name_plural = "지점효율 확인서(파일)"

    def __str__(self):
        return f"{self.month} / {self.branch} / {self.original_name or (self.file.name if self.file else '-')}"


# ------------------------------------------------------------
# ✅ 지점효율(행) — 정식 연결: confirm_group
# ------------------------------------------------------------
class EfficiencyChange(models.Model):
    requester = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="efficiency_requests")
    target = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="efficiency_targets")

    part = models.CharField(max_length=50, default="-")
    branch = models.CharField(max_length=50, default="-")
    month = models.CharField(max_length=7, db_index=True)  # "YYYY-MM"

    category = models.CharField(max_length=30, blank=True, default="")
    amount = models.PositiveIntegerField(null=True, blank=True)

    ded_name = models.CharField(max_length=50, blank=True, default="")
    ded_id = models.CharField(max_length=20, blank=True, default="")
    pay_name = models.CharField(max_length=50, blank=True, default="")
    pay_id = models.CharField(max_length=20, blank=True, default="")

    content = models.CharField(max_length=80, blank=True, default="")
    memo = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    process_date = models.DateField(null=True, blank=True)

    # ✅ 정식 연결 (Accordion/그룹 집계의 기준)
    confirm_group = models.ForeignKey(
        "partner.EfficiencyConfirmGroup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="efficiency_rows",
        verbose_name="확인서 그룹",
    )

    # ✅ 레거시 호환 (백필 완료 후 제거 가능)
    confirm_attachment = models.ForeignKey(
        "partner.EfficiencyConfirmAttachment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="efficiency_rows_legacy",
        verbose_name="확인서(레거시)",
    )

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["month", "branch"]),
            models.Index(fields=["confirm_group"]),
        ]

    def __str__(self):
        return f"{self.month} - {getattr(self.requester, 'name', '-')}"
