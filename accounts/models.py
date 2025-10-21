# django_ma/accounts/models.py
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
        ('superuser', 'Superuser'),
        ('main_admin', 'Main Admin'),
        ('sub_admin', 'Sub Admin'),
        ('basic', 'Basic'),
        ('inactive', 'Inactive'),
    ]

    grade = models.CharField(
        "권한등급",
        max_length=20,
        choices=GRADE_CHOICES,
        default='Basic'
    )

    id = models.CharField(max_length=30, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100, blank=True, null=True)
    grade = models.CharField(max_length=20, choices=GRADE_CHOICES, default='basic')
    status = models.CharField(max_length=20, default='재직')

    # ✅ 새로 추가되는 4개 필드
    regist = models.CharField(max_length=50, blank=True, null=True)
    birth = models.DateField("생년월일", blank=True, null=True)
    enter = models.DateField("입사일자", blank=True, null=True)
    quit = models.DateField("퇴사일자", blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.id} ({self.name})"

    class Meta:
        verbose_name = "users"
        verbose_name_plural = "users"

