# django_ma/partner/models.py
from django.db import models
from accounts.models import CustomUser


# ------------------------------------------------------------
# 📘 편제 변경 (조직 관리)
# ------------------------------------------------------------
class StructureChange(models.Model):
    """
    편제변경 메인 데이터 (Main Sheet)
    요청자(requester)가 대상자(target)에 대해 조직/직급/수수료율 변경을 요청한 기록
    """

    # 🔹 관계
    requester = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="structure_requests",
        help_text="변경 요청자"
    )
    target = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name="structure_targets",
        help_text="변경 대상자"
    )

    # 🔹 소속 정보
    part = models.CharField(max_length=50, blank=True, null=True, verbose_name="부서")
    branch = models.CharField(max_length=50, blank=True, null=True, help_text="요청자 소속")
    target_branch = models.CharField(max_length=50, blank=True, null=True, help_text="대상자 기존 소속")
    chg_branch = models.CharField(max_length=50, blank=True, null=True, help_text="변경 후 소속")

    # 🔹 직급 및 테이블 정보
    rank = models.CharField(max_length=20, blank=True, null=True)
    chg_rank = models.CharField(max_length=20, blank=True, null=True)
    table_name = models.CharField(max_length=20, blank=True, null=True)
    chg_table = models.CharField(max_length=20, blank=True, null=True)

    # 🔹 수수료율
    rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    chg_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    # 🔹 기타 정보
    memo = models.CharField(max_length=100, blank=True, null=True)
    or_flag = models.BooleanField(default=False, help_text="OR 여부 플래그")

    # 🔹 날짜
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


# ------------------------------------------------------------
# 📘 편제 변경 로그
# ------------------------------------------------------------
class PartnerChangeLog(models.Model):
    """
    편제변경 작업 로그
    (저장, 삭제, 마감설정 등 시스템 내 변경 내역 기록)
    """

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


# ------------------------------------------------------------
# 📘 편제 마감일 설정
# ------------------------------------------------------------
class StructureDeadline(models.Model):
    """
    편제 마감일 (월별/지점별)
    각 부서(branch)별로 마감일을 지정하여 변경 허용 기간을 제어
    """

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


# ------------------------------------------------------------
# 📘 권한관리 임시 테이블 (SubAdminTemp)
# ------------------------------------------------------------
class SubAdminTemp(models.Model):
    """
    권한관리 페이지 전용 확장 테이블 (CustomUser 기반)
    - CustomUser: id, name, part, branch, grade 기반
    - 여기에 팀/직급/세부등급 등 추가 관리
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="subadmin_detail")

    # 기본 참조용
    name = models.CharField(max_length=50)
    part = models.CharField(max_length=50, blank=True, null=True)
    branch = models.CharField(max_length=50, blank=True, null=True)
    grade = models.CharField(max_length=20, blank=True, null=True)

    # 권한관리 전용 세부 컬럼
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

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="-", verbose_name='레벨')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "partner_subadmin_temp"
        verbose_name = "권한관리 확장정보"
        verbose_name_plural = "권한관리 확장정보"

    def __str__(self):
        return f"{self.name} ({self.part})"

class TableSetting(models.Model):
    branch = models.CharField(max_length=100)      # 지점명
    table_name = models.CharField(max_length=100)  # 테이블명
    rate = models.CharField(max_length=20, blank=True, null=True)  # 요율 (%)
    order = models.PositiveIntegerField(default=0, help_text="표시 순서")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('branch', 'table_name')
        ordering = ['branch', 'table_name']

    def __str__(self):
        return f"{self.branch} - {self.table_name}"
    

# ------------------------------------------------------------
# 📘 요율관리용 테이블
# ------------------------------------------------------------
class RateTable(models.Model):
    """사용자별 요율관리용 테이블 (손보 / 생보 테이블 현황)"""

    user = models.OneToOneField(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='rate_table',
        verbose_name="사용자"
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
