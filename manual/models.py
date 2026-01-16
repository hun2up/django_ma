# django_ma/manual/models.py

from __future__ import annotations

from django.conf import settings
from django.db import models


# ============================================================
# Manual
# ============================================================

class Manual(models.Model):
    """
    ✅ 매뉴얼(문서) 엔티티

    접근 규칙(views에서 사용):
    - admin_only=True  : superuser/main_admin만 접근
    - is_published=False: superuser만 접근(직원전용/비공개 개념)

    정렬:
    - sort_order: 목록 정렬 우선순위(작을수록 위)
    """
    title = models.CharField(max_length=80)
    content = models.TextField(blank=True)

    admin_only = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-updated_at"]

    def __str__(self) -> str:
        return self.title


# ============================================================
# Section
# ============================================================

class ManualSection(models.Model):
    """
    ✅ '구역 카드(= section card)' 역할

    - manual     : 어느 매뉴얼에 속한 섹션인지
    - title      : 섹션 소제목
    - sort_order : 섹션 카드 정렬(작을수록 위)
    """
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=120, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "created_at"]

    def __str__(self) -> str:
        return f"[{self.manual_id}] section#{self.id}"


# ============================================================
# Block
# ============================================================

class ManualBlock(models.Model):
    """
    ✅ 블록(내용 카드) 역할

    - section : 어느 섹션 카드에 속하는지
    - content : Quill HTML 텍스트
    - image   : 좌측 이미지(썸네일/원본 팝업용)
    - sort_order : 섹션 내 블록 정렬

    ⚠️ manual FK는 section.manual로 추론 가능하므로 구조적으로 중복입니다.
       다만 기존 데이터/코드 호환을 위해 유지합니다.
       (추후 정리 마이그레이션에서 제거 권장)
    """
    manual = models.ForeignKey(Manual, on_delete=models.CASCADE, related_name="blocks")

    section = models.ForeignKey(
        ManualSection,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="blocks",
    )

    title = models.CharField(max_length=120, blank=True, default="")
    content = models.TextField(blank=True)

    image = models.ImageField(upload_to="manual/blocks/", blank=True, null=True)

    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "created_at"]

    def __str__(self) -> str:
        return f"block#{self.id} (section={self.section_id})"

    def delete(self, using=None, keep_parents=False):
        """
        ✅ 블록 삭제 시 좌측 이미지 파일도 함께 삭제

        - 첨부파일은 ManualBlockAttachment가 cascade로 삭제되며,
          각 attachment.delete()에서 파일도 삭제됨.
        """
        if self.image:
            self.image.delete(save=False)
        return super().delete(using=using, keep_parents=keep_parents)


# ============================================================
# Block Attachments
# ============================================================

class ManualBlockAttachment(models.Model):
    """
    ✅ 블록별 첨부파일 (N개 가능)

    - Quill 본문에는 링크(<a href="...">파일명</a>)로 삽입하는 방식
    - 실제 파일은 여기에서 관리(업로드/삭제/권한 통제 가능)
    """
    block = models.ForeignKey(
        ManualBlock, on_delete=models.CASCADE, related_name="attachments"
    )

    file = models.FileField(upload_to="manual/attachments/")
    original_name = models.CharField(max_length=255, blank=True, default="")
    size = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"attachment#{self.id} block={self.block_id}"

    def delete(self, using=None, keep_parents=False):
        """✅ 첨부 삭제 시 파일도 함께 삭제"""
        if self.file:
            self.file.delete(save=False)
        return super().delete(using=using, keep_parents=keep_parents)
