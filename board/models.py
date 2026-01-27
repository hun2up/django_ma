import mimetypes
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


# =========================================================
# Choices
# =========================================================
TASK_STATUS_CHOICES = [
    ("시작전", "시작전"),
    ("진행중", "진행중"),
    ("보완필요", "보완필요"),
    ("완료", "완료"),
]


# =========================================================
# Post (업무요청)
# =========================================================
class Post(models.Model):
    """
    업무요청 게시글
    - 접수번호: YYYYMMDD### 자동 생성
    - status/handler 변경 시 status_updated_at 갱신
    """

    # 기본 정보
    receipt_number = models.CharField("접수번호", max_length=20, unique=True, blank=True)
    category = models.CharField("구분", max_length=10, blank=True, default="")
    fa = models.CharField("성명(대상자)", max_length=20, blank=True, default="")
    code = models.IntegerField(
        "사번(대상자)",
        validators=[MinValueValidator(1600000), MaxValueValidator(3000000)],
        null=True,
        blank=True,
    )

    # 본문
    title = models.CharField("제목", max_length=200)
    content = models.TextField("요청 내용")

    # 작성자 정보(스냅샷)
    user_id = models.CharField("사번(요청자)", max_length=30, blank=True)
    user_name = models.CharField("성명(요청자)", max_length=100, blank=True)
    user_branch = models.CharField("소속(요청자)", max_length=100, blank=True)

    created_at = models.DateTimeField("최초등록일", auto_now_add=True)

    # 담당자/상태
    handler = models.CharField("담당자", max_length=100, blank=True, default="")

    STATUS_CHOICES = [
        ("확인중", "확인중"),
        ("진행중", "진행중"),
        ("보완요청", "보완요청"),
        ("완료", "완료"),
        ("반려", "반려"),
    ]
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default="확인중")
    status_updated_at = models.DateTimeField("상태변경일", blank=True, null=True)

    def save(self, *args, **kwargs):
        """
        - receipt_number 자동 생성
        - status/handler 변경 시 status_updated_at 갱신
        - update_fields 사용 시 status_updated_at 누락 방지
        """
        now = timezone.localtime()
        update_fields = kwargs.get("update_fields")

        # None 방어
        if self.handler is None:
            self.handler = ""

        # 접수번호 자동 생성
        if not self.receipt_number:
            today_str = now.strftime("%Y%m%d")
            last = (
                Post.objects.filter(created_at__date=now.date(), receipt_number__startswith=today_str)
                .order_by("-receipt_number")
                .values_list("receipt_number", flat=True)
                .first()
            )
            seq = int(last[-3:]) + 1 if (last and len(last) >= 11) else 1
            self.receipt_number = f"{today_str}{seq:03d}"

        # 상태변경일 갱신 여부 판단
        touch = False
        if self.pk:
            prev = Post.objects.filter(pk=self.pk).only("status", "handler").first()
            if prev and (prev.status != self.status or prev.handler != self.handler):
                touch = True
        else:
            touch = True

        if touch:
            self.status_updated_at = now
            if update_fields is not None:
                uf = set(update_fields)
                uf.add("status_updated_at")
                if not self.pk:
                    uf.add("receipt_number")
                kwargs["update_fields"] = list(uf)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.receipt_number}] {self.title}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "업무요청 게시글"
        verbose_name_plural = "업무요청 게시글 목록"


# =========================================================
# Task (직원업무) - superuser만 접근(권한은 views에서)
# =========================================================
class Task(models.Model):
    """
    직원업무 게시글
    - 접수번호: YYYYMMDD### 자동 생성
    - status/handler 변경 시 status_updated_at 갱신
    """

    receipt_number = models.CharField("접수번호", max_length=20, unique=True, blank=True)
    category = models.CharField("구분", max_length=10, blank=True, default="")

    title = models.CharField("제목", max_length=200)
    content = models.TextField("요청 내용")

    user_id = models.CharField("사번(요청자)", max_length=30, blank=True, default="")
    user_name = models.CharField("성명(요청자)", max_length=100, blank=True, default="")
    user_branch = models.CharField("소속(요청자)", max_length=100, blank=True, default="")

    created_at = models.DateTimeField("최초등록일", auto_now_add=True)

    handler = models.CharField("담당자", max_length=100, blank=True, default="")
    status = models.CharField("상태", max_length=20, choices=TASK_STATUS_CHOICES, default="시작전")
    status_updated_at = models.DateTimeField("상태변경일", blank=True, null=True)

    def save(self, *args, **kwargs):
        now = timezone.localtime()
        update_fields = kwargs.get("update_fields")

        # None 방어
        self.user_id = self.user_id or ""
        self.user_name = self.user_name or ""
        self.user_branch = self.user_branch or ""
        self.handler = self.handler or ""

        # 접수번호 생성
        if not self.receipt_number:
            today_str = now.strftime("%Y%m%d")
            last = (
                Task.objects.filter(created_at__date=now.date(), receipt_number__startswith=today_str)
                .order_by("-receipt_number")
                .values_list("receipt_number", flat=True)
                .first()
            )
            seq = int(last[-3:]) + 1 if (last and len(last) >= 11) else 1
            self.receipt_number = f"{today_str}{seq:03d}"

        # 상태변경일 갱신 여부 판단
        touch = False
        if self.pk:
            prev = Task.objects.filter(pk=self.pk).only("status", "handler").first()
            if prev and (prev.status != self.status or prev.handler != self.handler):
                touch = True
        else:
            touch = True

        if touch:
            self.status_updated_at = now
            if update_fields is not None:
                uf = set(update_fields)
                uf.add("status_updated_at")
                if not self.pk:
                    uf.add("receipt_number")
                kwargs["update_fields"] = list(uf)

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "직원업무 게시글"
        verbose_name_plural = "직원업무 게시글 목록"


# =========================================================
# Attachments / Comments
# =========================================================
def attachment_upload_to(instance, filename):
    return f"attachments/{timezone.now():%Y/%m/%d}/{filename}"


class Attachment(models.Model):
    post = models.ForeignKey(Post, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_upload_to)

    original_name = models.CharField("원본 파일명", max_length=255, blank=True)
    size = models.PositiveBigIntegerField("파일 크기", default=0)
    content_type = models.CharField("MIME 타입", max_length=120, blank=True)
    uploaded_at = models.DateTimeField("업로드일", auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file:
            self.original_name = getattr(self.file, "name", self.original_name)
            self.size = getattr(self.file, "size", self.size)
            if not self.content_type:
                guessed, _ = mimetypes.guess_type(self.original_name or "")
                self.content_type = guessed or "application/octet-stream"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.original_name or getattr(self.file, "name", "")

    class Meta:
        verbose_name = "첨부파일"
        verbose_name_plural = "첨부파일 목록"


class Comment(models.Model):
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


# ----------------- Task Attachments / Comments -----------------
def task_attachment_upload_to(instance, filename):
    return f"task_attachments/{timezone.now():%Y/%m/%d}/{filename}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to=task_attachment_upload_to)

    original_name = models.CharField("원본 파일명", max_length=255, blank=True)
    size = models.PositiveBigIntegerField("파일 크기", default=0)
    content_type = models.CharField("MIME 타입", max_length=120, blank=True)
    uploaded_at = models.DateTimeField("업로드일", auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.file:
            self.original_name = getattr(self.file, "name", self.original_name)
            self.size = getattr(self.file, "size", self.size)
            if not self.content_type:
                guessed, _ = mimetypes.guess_type(self.original_name or "")
                self.content_type = guessed or "application/octet-stream"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "직원업무 첨부파일"
        verbose_name_plural = "직원업무 첨부파일 목록"


class TaskComment(models.Model):
    task = models.ForeignKey(Task, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField("댓글 내용", max_length=500)
    created_at = models.DateTimeField("작성일시", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "직원업무 댓글"
        verbose_name_plural = "직원업무 댓글 목록"
