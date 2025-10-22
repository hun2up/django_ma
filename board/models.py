# ===========================================
# 📂 django_ma/board/models.py — 업무요청 게시판 모델 정의
# ===========================================

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import mimetypes


# ===========================================
# 📌 [1] 업무요청 게시글(Post)
# ===========================================
class Post(models.Model):
    """
    업무요청 게시글 모델
    - 접수번호는 날짜별 자동 생성 (예: 20251015001)
    - 담당자 또는 상태 변경 시 '상태변경일' 자동 갱신
    """

    # === 기본 정보 ===
    receipt_number = models.CharField(
        "접수번호",
        max_length=20,
        unique=True,
        blank=True,
        help_text="자동 생성 (예: 20251015001)"
    )
    category = models.CharField("구분", max_length=10, blank=True, default="")
    fa = models.CharField("성명(대상자)", max_length=20, blank=True, default="")
    code = models.IntegerField(
        "사번(대상자)",
        validators=[MinValueValidator(1600000), MaxValueValidator(3000000)],
        null=True, blank=True
    )

    # === 게시글 본문 ===
    title = models.CharField("제목", max_length=200)
    content = models.TextField("요청 내용")

    # === 요청자 정보 ===
    user_id = models.CharField("사번(요청자)", max_length=30, blank=True)
    user_name = models.CharField("성명(요청자)", max_length=100, blank=True)
    user_branch = models.CharField("소속(요청자)", max_length=100, blank=True)

    created_at = models.DateTimeField("최초등록일", auto_now_add=True)

    # === 담당자 및 상태 관리 ===
    handler = models.CharField(
        "담당자",
        max_length=100,
        blank=True,
        default="",
        help_text="담당자(슈퍼유저 이름)"
    )

    STATUS_CHOICES = [
        ("확인중", "확인중"),
        ("진행중", "진행중"),
        ("보완요청", "보완요청"),
        ("완료", "완료"),
        ("반려", "반려"),
    ]
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default="확인중")

    status_updated_at = models.DateTimeField(
        "상태변경일",
        blank=True, null=True,
        help_text="상태나 담당자가 변경된 시점 자동기록"
    )

    # ===========================================
    # 🧩 저장 로직 (자동 필드 갱신)
    # ===========================================
    def save(self, *args, **kwargs):
        """저장 시 접수번호 생성 및 상태변경일 자동 기록"""
        now = timezone.localtime()

        # ✅ 신규 접수번호 자동 생성 (YYYYMMDD###)
        if not self.receipt_number:
            today_str = now.strftime("%Y%m%d")
            count_today = Post.objects.filter(created_at__date=now.date()).count() + 1
            self.receipt_number = f"{today_str}{count_today:03d}"

        # ✅ 기존 레코드일 경우 상태/담당자 변경 감지
        if self.pk:
            previous = Post.objects.filter(pk=self.pk).only("status", "handler").first()
            if previous and (
                previous.status != self.status or previous.handler != self.handler
            ):
                self.status_updated_at = now
        else:
            # 신규 생성 시 최초 상태기록
            self.status_updated_at = now

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.receipt_number}] {self.title}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "업무요청 게시글"
        verbose_name_plural = "업무요청 게시글 목록"


# ===========================================
# 📌 [2] 첨부파일(Attachment)
# ===========================================
def attachment_upload_to(instance, filename):
    """업로드 경로: media/attachments/연도/월/일/파일명"""
    return f"attachments/{timezone.now():%Y/%m/%d}/{filename}"


class Attachment(models.Model):
    """
    첨부파일 모델
    - 업로드 시 자동으로 파일명, 크기, MIME 타입 기록
    - 게시글(Post) 삭제 시 연동 삭제 (CASCADE)
    """

    post = models.ForeignKey(Post, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_upload_to)

    original_name = models.CharField("원본 파일명", max_length=255, blank=True)
    size = models.PositiveBigIntegerField("파일 크기", default=0)
    content_type = models.CharField("MIME 타입", max_length=120, blank=True)
    uploaded_at = models.DateTimeField("업로드일", auto_now_add=True)

    def save(self, *args, **kwargs):
        """파일 저장 시 원본명·크기·타입 자동 갱신"""
        if self.file:
            self.original_name = getattr(self.file, "name", self.original_name)
            self.size = getattr(self.file, "size", self.size)
            if not self.content_type:
                guessed, _ = mimetypes.guess_type(self.original_name or "")
                self.content_type = guessed or "application/octet-stream"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or self.file.name

    class Meta:
        verbose_name = "첨부파일"
        verbose_name_plural = "첨부파일 목록"


# ===========================================
# 📌 [3] 댓글(Comment)
# ===========================================
class Comment(models.Model):
    """
    댓글 모델
    - 게시글(Post)과 1:N 관계
    - 작성자(author)는 사용자(CustomUser)
    """

    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField("댓글 내용", max_length=500)
    created_at = models.DateTimeField("작성일시", auto_now_add=True)

    def __str__(self):
        return f"{self.author} - {self.content[:20]}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "댓글"
        verbose_name_plural = "댓글 목록"
