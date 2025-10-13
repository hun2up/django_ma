from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, id, password=None, **extra_fields):
        if not id:
            raise ValueError("ID는 반드시 입력되어야 합니다.")
        user = self.model(id=id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, id, password=None, **extra_fields):
        extra_fields.setdefault('grade', 'superuser')
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(id, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    GRADE_CHOICES = [
        ('superuser', 'Superuser'),  # 최고 관리자
        ('admin', 'Admin'),          # 관리자
        ('basic', 'Basic'),          # 일반 사용자
        ('inactive', 'Inactive'),    # 퇴사자 또는 비활성화
    ]

    id = models.CharField(max_length=30, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100, blank=True, null=True)
    grade = models.CharField(
        max_length=20,
        choices=GRADE_CHOICES,
        default='basic',  # ✅ 존재하는 choice 값으로 수정
    )
    status = models.CharField(max_length=20, default='재직')  # 예: 재직, 퇴사 등

    is_active = models.BooleanField(default=True)   # 로그인 가능 여부
    is_staff = models.BooleanField(default=False)   # admin site 접근 가능 여부
    is_superuser = models.BooleanField(default=False)  # 전체 권한 여부

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.id} ({self.name})"

    class Meta:
        verbose_name = "users"
        verbose_name_plural = "users"
