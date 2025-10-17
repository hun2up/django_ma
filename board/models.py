# django_ma/board/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import mimetypes
from django.conf import settings

class Post(models.Model):
    """
    업무요청 게시글 모델
    - 접수번호는 날짜별 자동 생성 (YYYYMMDD###)
    - 담당자/상태 변경 시 상태변경일 자동 갱신
    """

    # === 기본 정보 ===
    receipt_number = models.CharField(
        "접수번호",
        max_length=20,
        unique=True,
        blank=True,
        help_text="자동 생성 (예: 20251015001)"
    )
    category = models.CharField("구분", max_length=7, default="", blank=True)
    fa = models.CharField("성명(대상자)", max_length=20, default="", blank=True)
    code = models.IntegerField(
        "사번(대상자)",
        validators=[MinValueValidator(1600000), MaxValueValidator(3000000)],
        blank=True,
        null=True
    )

    title = models.CharField("제목", max_length=200)
    content = models.TextField("요청 내용")

    # === 작성자 정보 ===
    user_id = models.CharField("사번(요청자)", max_length=30, blank=True)
    user_name = models.CharField("성명(요청자)", max_length=100, blank=True)
    user_branch = models.CharField("소속(요청자)", max_length=100, blank=True)

    created_at = models.DateTimeField("최초등록일", auto_now_add=True)

    # === 담당자 / 상태 관리 ===
    handler = models.CharField(
        "담당자",
        max_length=100,
        blank=True,
        default="",
        help_text="담당자(슈퍼유저 이름)"
    )

    STATUS_CHOICES = [
        ('확인중', '확인중'),
        ('진행중', '진행중'),
        ('보완요청', '보완요청'),
        ('완료', '완료'),
        ('반려', '반려'),
    ]
    status = models.CharField(
        "상태",
        max_length=20,
        choices=STATUS_CHOICES,
        default='확인중'
    )
    status_updated_at = models.DateTimeField(
        "상태변경일",
        blank=True,
        null=True,
        help_text="상태나 담당자가 변경된 시점"
    )

    def save(self, *args, **kwargs):
        """저장 시 접수번호 및 상태/담당자 변경일 자동 처리"""
        now = timezone.localtime()

        # ✅ 접수번호 자동 생성
        if not self.receipt_number:
            today_str = now.strftime('%Y%m%d')
            count_today = Post.objects.filter(created_at__date=now.date()).count() + 1
            self.receipt_number = f"{today_str}{count_today:03d}"

        # ✅ 기존 객체라면 상태 또는 담당자 변경 감지
        if self.pk:
            previous = Post.objects.filter(pk=self.pk).first()
            if previous and (
                previous.status != self.status or previous.handler != self.handler
            ):
                self.status_updated_at = now
        else:
            # 새 객체라면 최초 생성 시점 기록
            self.status_updated_at = now

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.receipt_number}] {self.title}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Posts"
        verbose_name_plural = "Posts"


# === 첨부파일 관련 ===
def attachment_upload_to(instance, filename):
    """업로드 경로: media/attachments/연도/월/일/파일명"""
    return f"attachments/{timezone.now():%Y/%m/%d}/{filename}"


class Attachment(models.Model):
    post = models.ForeignKey(Post, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_upload_to)
    original_name = models.CharField(max_length=255, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """파일 저장 시 원본 이름, 용량, MIME 타입 자동 기록"""
        if self.file and not self.original_name:
            self.original_name = getattr(self.file, 'name', '')
        if self.file and hasattr(self.file, 'size'):
            self.size = self.file.size or 0
        if self.file and not self.content_type:
            guessed, _ = mimetypes.guess_type(self.original_name or '')
            self.content_type = guessed or ''
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or self.file.name


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author} - {self.content[:20]}"