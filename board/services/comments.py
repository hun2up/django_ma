# django_ma/board/services/comments.py
# =========================================================
# Comment Services
# - Post/Task 공용 댓글 처리(등록/수정/삭제)
# - 기존 로직을 그대로 이동(기능 영향 최소화)
# =========================================================

from __future__ import annotations

from typing import Optional

from django.contrib import messages
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect


def handle_comments_actions(
    *,
    request: HttpRequest,
    obj,
    comment_model,
    fk_field: str,
    redirect_detail_name: str,
) -> Optional[object]:
    """
    ✅ 댓글 등록/수정/삭제 공용 처리
    - POST(action_type): comment | edit_comment | delete_comment
    - 처리했으면 redirect response를 반환하고, 아니면 None
    """
    act = (request.POST.get("action_type") or "").strip()

    # ---------------------------------------------------------
    # ✅ 등록
    # ---------------------------------------------------------
    if act == "comment":
        content = (request.POST.get("content") or "").strip()
        if content:
            comment_model.objects.create(**{fk_field: obj, "author": request.user, "content": content})
            messages.success(request, "댓글 등록 완료")
        else:
            messages.error(request, "댓글 내용을 입력해주세요.")
        return redirect(redirect_detail_name, pk=obj.pk)

    # ---------------------------------------------------------
    # ✅ 수정 (작성자만)
    # ---------------------------------------------------------
    if act == "edit_comment":
        comment_id = request.POST.get("comment_id")
        content = (request.POST.get("content") or "").strip()
        if not content:
            messages.error(request, "댓글 내용을 입력해주세요.")
            return redirect(redirect_detail_name, pk=obj.pk)

        c = get_object_or_404(comment_model, id=comment_id, author=request.user, **{fk_field: obj})
        c.content = content
        c.save(update_fields=["content"])
        messages.success(request, "댓글 수정 완료")
        return redirect(redirect_detail_name, pk=obj.pk)

    # ---------------------------------------------------------
    # ✅ 삭제 (작성자만)
    # ---------------------------------------------------------
    if act == "delete_comment":
        comment_id = request.POST.get("comment_id")
        comment_model.objects.filter(id=comment_id, author=request.user, **{fk_field: obj}).delete()
        messages.info(request, "댓글 삭제 완료")
        return redirect(redirect_detail_name, pk=obj.pk)

    return None
