from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, id, password=None, **extra_fields):
        if not id:
            raise ValueError('The ID field is required.')
        user = self.model(id=id, **extra_fields)
        user.set_password(password)  # 비밀번호 암호화
        user.save(using=self._db)
        return user

    def create_superuser(self, id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('grade', 'superuser')  # 기본 등급 설정
        return self.create_user(id, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    # 기본 필드
    id = models.CharField(max_length=30, unique=True, primary_key=True)  # 로그인 ID
    name = models.CharField(max_length=50, verbose_name="Name")
    branch = models.CharField(max_length=100, verbose_name="Branch")
    
    # grade는 Django의 권한 시스템과 연계
    grade = models.CharField(
        max_length=20,
        choices=[
            ('staff', 'Staff'),
            ('superuser', 'Superuser'),
            ('active', 'Active'),
        ],
        default='active',
        verbose_name="Grade"
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('재직', '재직'),
            ('퇴사', '퇴사'),
            ('휴직', '휴직'),
        ],
        default='재직',
        verbose_name="Status"
    )

    # Django 권한 관련 기본 필드
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Django Admin 접근 여부
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'id'  # 로그인용 필드 지정
    REQUIRED_FIELDS = []   # createsuperuser 시 추가 입력 없음

    def __str__(self):
        return f"{self.id} ({self.name})"
