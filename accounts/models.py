from __future__ import annotations

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# =============================================================================
# 1) Custom User Manager
# =============================================================================
class CustomUserManager(BaseUserManager):
    """
    - create_user: 일반 사용자 생성
    - create_superuser: 관리자 생성
    """

    def create_user(self, id, password=None, **extra_fields):
        if not id:
            raise ValueError("ID는 반드시 입력되어야 합니다.")

        user = self.model(id=id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, id, password=None, **extra_fields):
        # 관리자 기본 속성 강제
        extra_fields.setdefault("grade", "superuser")
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(id=id, password=password, **extra_fields)


# =============================================================================
# 2) Custom User Model
#    조직 위계: channel(부문) > division(총괄) > part(부서) > branch(지점)
# =============================================================================
class CustomUser(AbstractBaseUser, PermissionsMixin):
    # -------------------------------------------------------------------------
    # 권한 등급
    # -------------------------------------------------------------------------
    GRADE_CHOICES = [
        ("superuser", "Superuser"),
        ("main_admin", "Main Admin"),
        ("sub_admin", "Sub Admin"),
        ("basic", "Basic"),
        ("resign", "Resign"),
        ("inactive", "Inactive"),
    ]

    # -------------------------------------------------------------------------
    # 기본 식별/개인정보
    # -------------------------------------------------------------------------
    id = models.CharField(max_length=30, unique=True, primary_key=True)  # 사원번호
    name = models.CharField(max_length=100)

    regist = models.CharField(max_length=50, blank=True, null=True)
    birth = models.DateField("생년월일", blank=True, null=True)
    enter = models.DateField("입사일자", blank=True, null=True)
    quit = models.DateField("퇴사일자", blank=True, null=True)

    # -------------------------------------------------------------------------
    # 조직 정보 (위계)
    # -------------------------------------------------------------------------
    channel = models.CharField(max_length=10, blank=True, default="", verbose_name="부문")
    division = models.CharField(max_length=30, blank=True, null=True, default="", verbose_name="총괄")
    part = models.CharField(max_length=10, blank=True, default="", verbose_name="부서")
    branch = models.CharField(max_length=100, blank=True, null=True, verbose_name="지점")

    # -------------------------------------------------------------------------
    # 권한/상태
    # -------------------------------------------------------------------------
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES, default="basic")
    status = models.CharField(max_length=20, default="재직")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # -------------------------------------------------------------------------
    # Django auth config
    # -------------------------------------------------------------------------
    USERNAME_FIELD = "id"
    REQUIRED_FIELDS = ["name"]

    objects = CustomUserManager()

    # -------------------------------------------------------------------------
    # 기타
    # -------------------------------------------------------------------------
    def __str__(self):
        return f"{self.id} ({self.name})"

    class Meta:
        verbose_name = "users"
        verbose_name_plural = "users"
