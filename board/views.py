# django_ma/board/views.py
# =========================================================
# Board App Views (FINAL REFACTOR)
#
# ✅ Policy
# - board(app) 기본 기능: superuser / head / leader
# - task(직원업무): superuser only
#
# ✅ Goals
# - 가독성/유지보수성 향상: 상수/유틸 SSOT, 코드 재정렬, 주석 정리
# - URL name 상수화, 필터/페이지네이션 유틸 정리
# - support_form / states_form: SSOT 컨텍스트 사용
# =========================================================

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Tuple, Callable, Dict, List

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, QuerySet
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.search_api import search_users_for_api

from .forms import PostForm, CommentForm, TaskForm, TaskCommentForm
from .models import (
    Post, Attachment, Comment,
    Task, TaskAttachment, TaskComment, TASK_STATUS_CHOICES,
)

from board.utils.pdf_support_utils import generate_request_support as build_support
from board.utils.pdf_states_utils import generate_request_states as build_states

logger = logging.getLogger("board.access")
User = get_user_model()

# =========================================================
# ✅ Permission Policy
# =========================================================
BOARD_ALLOWED_GRADES = ("superuser", "head", "leader")   # board 대부분 기능
TASK_ALLOWED_GRADES = ("superuser",)                    # 직원업무(task) 전용

# =========================================================
# ✅ Constants
# =========================================================
STATUS_CHOICES = ["확인중", "진행중", "보완요청", "완료", "반려"]
TASK_STATUS_VALUES = [s[0] for s in TASK_STATUS_CHOICES]

POST_CATEGORY_VALUES = ["위해촉", "리스크/유지율", "수수료/채권", "운영자금", "전산", "기타"]
TASK_CATEGORY_VALUES = ["위해촉", "리스크/유지율", "수수료/채권", "운영자금", "전산", "기타", "민원", "신규제휴"]

PER_PAGE_CHOICES = [10, 25, 50, 100]
INLINE_ACTIONS = ("handler", "status")

# URL Names (reverse/redirect에서 raw string 금지)
POST_DETAIL = "board:post_detail"
POST_LIST = "board:post_list"
POST_EDIT = "board:post_edit"

TASK_DETAIL = "board:task_detail"
TASK_LIST = "board:task_list"
TASK_EDIT = "board:task_edit"

SUPPORT_FORM = "board:support_form"
STATES_FORM = "board:states_form"

# ---------------------------------------------------------
# ✅ Form UI Constants (SSOT)
# ---------------------------------------------------------
SUPPORT_TARGET_FIELDS = [
    ("성명", "target_name_"),
    ("사번", "target_code_"),
    ("입사일", "target_join_"),
    ("퇴사일", "target_leave_"),
]

SUPPORT_CONTRACT_FIELDS = [
    ("보험사", "insurer_", 3),
    ("증권번호", "policy_no_", 3),
    ("계약자(피보험자)", "contractor_", 3),
    ("보험료", "premium_", 2),
]


def _build_support_form_context() -> Dict[str, Any]:
    """
    support_form / states_form 공용 컨텍스트 생성(SSOT).
    - templates expected: fields, contracts
    """
    return {
        "fields": SUPPORT_TARGET_FIELDS,
        "contracts": SUPPORT_CONTRACT_FIELDS,
    }


# =========================================================
# ✅ List Utils (filters / paging)
# =========================================================
def _get_handlers() -> List[str]:
    """담당자 목록: superuser의 name만 노출(기존 정책 유지)"""
    return list(User.objects.filter(grade="superuser").values_list("name", flat=True))


def _get_per_page(request: HttpRequest, default: int = 10) -> int:
    raw = str(request.GET.get("per_page", "")).strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return n if n in PER_PAGE_CHOICES else default


def _build_query_string_without_page(request: HttpRequest) -> str:
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def _parse_date_range(request: HttpRequest) -> Tuple[str, str, Optional[Any], Optional[Any]]:
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    return date_from_raw, date_to_raw, date_from, date_to


def _apply_keyword_filter(
    qs: QuerySet,
    keyword: str,
    search_type: str,
    *,
    title_field: str,
    content_field: str,
    user_name_field: str,
) -> QuerySet:
    """검색 타입(title/content/title_content/user_name)에 따른 keyword 필터"""
    if not keyword:
        return qs

    if search_type == "title":
        return qs.filter(**{f"{title_field}__icontains": keyword})
    if search_type == "content":
        return qs.filter(**{f"{content_field}__icontains": keyword})
    if search_type == "title_content":
        return qs.filter(
            Q(**{f"{title_field}__icontains": keyword}) |
            Q(**{f"{content_field}__icontains": keyword})
        )
    if search_type == "user_name":
        return qs.filter(**{f"{user_name_field}__icontains": keyword})

    # fallback
    return qs.filter(**{f"{title_field}__icontains": keyword})


def _apply_common_list_filters(
    qs: QuerySet,
    *,
    date_from,
    date_to,
    selected_category: str,
    selected_handler: str,
    selected_status: str,
    category_field: str = "category",
    handler_field: str = "handler",
    status_field: str = "status",
    created_field: str = "created_at",
) -> QuerySet:
    """게시판 목록 공용 필터(기간/카테고리/담당자/상태)"""
    if date_from:
        qs = qs.filter(**{f"{created_field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{created_field}__date__lte": date_to})

    if selected_category and selected_category != "전체":
        qs = qs.filter(**{f"{category_field}__iexact": selected_category})

    if selected_handler != "전체":
        qs = qs.filter(**{handler_field: selected_handler})

    if selected_status != "전체":
        qs = qs.filter(**{status_field: selected_status})

    return qs


def _paginate(request: HttpRequest, qs: QuerySet, *, default_per_page: int = 10):
    per_page = _get_per_page(request, default=default_per_page)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    return page_obj, per_page


@dataclass(frozen=True)
class ListParams:
    keyword: str
    search_type: str
    selected_handler: str
    selected_status: str
    selected_category: str
    date_from_raw: str
    date_to_raw: str
    date_from: Optional[Any]
    date_to: Optional[Any]


def _read_list_params(request: HttpRequest) -> ListParams:
    keyword = (request.GET.get("keyword") or "").strip()
    search_type = (request.GET.get("search_type") or "title").strip()

    selected_handler = (request.GET.get("handler") or "전체").strip()
    selected_status = (request.GET.get("status") or "전체").strip()
    selected_category = (request.GET.get("category") or "전체").strip()

    date_from_raw, date_to_raw, date_from, date_to = _parse_date_range(request)

    return ListParams(
        keyword=keyword,
        search_type=search_type,
        selected_handler=selected_handler,
        selected_status=selected_status,
        selected_category=selected_category,
        date_from_raw=date_from_raw,
        date_to_raw=date_to_raw,
        date_from=date_from,
        date_to=date_to,
    )


# =========================================================
# ✅ Common Actions (comments / attachments / inline update)
# =========================================================
def _handle_comments_actions(*, request: HttpRequest, obj, comment_model, fk_field: str, redirect_detail_name: str):
    """
    댓글 등록/수정/삭제 공용 처리
    - POST(action_type): comment | edit_comment | delete_comment
    """
    act = (request.POST.get("action_type") or "").strip()

    if act == "comment":
        content = (request.POST.get("content") or "").strip()
        if content:
            comment_model.objects.create(**{fk_field: obj, "author": request.user, "content": content})
            messages.success(request, "댓글 등록 완료")
        else:
            messages.error(request, "댓글 내용을 입력해주세요.")
        return redirect(redirect_detail_name, pk=obj.pk)

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

    if act == "delete_comment":
        comment_id = request.POST.get("comment_id")
        comment_model.objects.filter(id=comment_id, author=request.user, **{fk_field: obj}).delete()
        messages.info(request, "댓글 삭제 완료")
        return redirect(redirect_detail_name, pk=obj.pk)

    return None


def _save_attachments(*, files: Iterable, create_func: Callable[..., Any]) -> None:
    """
    files: request.FILES.getlist("attachments")
    create_func: Attachment/TaskAttachment create 래퍼
    """
    for f in files:
        create_func(
            file=f,
            original_name=getattr(f, "name", "") or "",
            size=getattr(f, "size", 0) or 0,
            content_type=getattr(f, "content_type", "") or "",
        )


def _inline_update_common(
    *,
    obj,
    action: str,
    value: str,
    allowed_status_values: List[str],
) -> JsonResponse:
    """
    인라인 담당자/상태 업데이트 공용 처리(Post/Task 공용)
    - action: handler | status
    """
    now = timezone.localtime()

    if action == "handler":
        obj.handler = "" if value in ("", "선택") else value
        obj.status_updated_at = now
        obj.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{obj.handler or '미지정'}'로 변경되었습니다.",
            "handler": obj.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    if value not in allowed_status_values:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    obj.status = value
    obj.status_updated_at = now
    obj.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{obj.status}'로 변경되었습니다.",
        "status": obj.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })


# =========================================================
# ✅ Task (직원업무) — superuser only
# =========================================================
@login_required
@grade_required(*TASK_ALLOWED_GRADES)
def task_list(request: HttpRequest) -> HttpResponse:
    p = _read_list_params(request)

    qs = (
        Task.objects
        .annotate(comment_count=Count("comments", distinct=True))
        .order_by("-created_at")
    )

    qs = _apply_keyword_filter(
        qs, p.keyword, p.search_type,
        title_field="title",
        content_field="content",
        user_name_field="user_name",
    )
    qs = _apply_common_list_filters(
        qs,
        date_from=p.date_from,
        date_to=p.date_to,
        selected_category=p.selected_category,
        selected_handler=p.selected_handler,
        selected_status=p.selected_status,
    )

    tasks, per_page = _paginate(request, qs, default_per_page=10)
    query_string = _build_query_string_without_page(request)

    return render(request, "board/task_list.html", {
        "tasks": tasks,
        "per_page": per_page,
        "per_page_choices": PER_PAGE_CHOICES,
        "query_string": query_string,
        "is_superuser": True,

        "handlers": _get_handlers(),
        "keyword": p.keyword,
        "search_type": p.search_type,
        "selected_handler": p.selected_handler,
        "selected_status": p.selected_status,
        "status_choices": TASK_STATUS_VALUES,

        "category_choices": TASK_CATEGORY_VALUES,
        "selected_category": p.selected_category,
        "date_from": p.date_from_raw,
        "date_to": p.date_to_raw,
    })


@login_required
@grade_required(*TASK_ALLOWED_GRADES)
@require_POST
def ajax_update_task_field(request: HttpRequest) -> JsonResponse:
    task_id = request.POST.get("task_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or request.POST.get(action) or "").strip()

    if not task_id or action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, id=task_id)
    return _inline_update_common(obj=task, action=action, value=value, allowed_status_values=TASK_STATUS_VALUES)


@login_required
@grade_required(*TASK_ALLOWED_GRADES)
@require_POST
def ajax_update_task_field_detail(request: HttpRequest, pk: int) -> JsonResponse:
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, pk=pk)
    return _inline_update_common(obj=task, action=action, value=value, allowed_status_values=TASK_STATUS_VALUES)


@login_required
@grade_required(*TASK_ALLOWED_GRADES)
def task_detail(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        act = (request.POST.get("action_type") or "").strip()

        handled = _handle_comments_actions(
            request=request,
            obj=task,
            comment_model=TaskComment,
            fk_field="task",
            redirect_detail_name=TASK_DETAIL,
        )
        if handled:
            return handled

        if act == "delete_task":
            task.delete()
            messages.success(request, "게시글이 삭제되었습니다.")
            return redirect(TASK_LIST)

        return redirect(TASK_DETAIL, pk=pk)

    task_info = {
        "소속(요청자)": task.user_branch,
        "성명(요청자)": task.user_name,
        "사번(요청자)": task.user_id,
    }

    return render(request, "board/task_detail.html", {
        "task": task,
        "task_info": task_info,
        "is_superuser": True,
        "can_edit": True,

        "handlers": _get_handlers(),
        "comments": task.comments.order_by("-created_at"),
        "attachments": task.attachments.all(),
        "form": TaskCommentForm(),

        "detail_url": reverse(TASK_DETAIL, kwargs={"pk": task.pk}),
        "list_url": reverse(TASK_LIST),
        "edit_url": reverse(TASK_EDIT, kwargs={"pk": task.pk}),
        "status_choices": TASK_STATUS_VALUES,
    })


@login_required
@grade_required(*TASK_ALLOWED_GRADES)
def task_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.user_id = str(request.user.id)
            task.user_name = getattr(request.user, "name", "") or ""
            task.user_branch = getattr(request.user, "branch", "") or ""
            task.save()

            files = request.FILES.getlist("attachments")

            def _create_task_attachment(**kwargs):
                return TaskAttachment.objects.create(task=task, **kwargs)

            _save_attachments(files=files, create_func=_create_task_attachment)

            messages.success(request, "게시글이 등록되었습니다.")
            return redirect(TASK_DETAIL, pk=task.pk)

        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = TaskForm()

    return render(request, "board/task_create.html", {"form": form})


@login_required
@grade_required(*TASK_ALLOWED_GRADES)
def task_edit(request: HttpRequest, pk: int) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = TaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.user_id = task.user_id or str(request.user.id)
            task.user_name = task.user_name or getattr(request.user, "name", "") or ""
            task.user_branch = task.user_branch or getattr(request.user, "branch", "") or ""
            task.save()

            del_ids = request.POST.getlist("delete_files")
            if del_ids:
                TaskAttachment.objects.filter(id__in=del_ids, task=task).delete()

            files = request.FILES.getlist("attachments")

            def _create_task_attachment(**kwargs):
                return TaskAttachment.objects.create(task=task, **kwargs)

            _save_attachments(files=files, create_func=_create_task_attachment)

            messages.success(request, "게시글이 수정되었습니다.")
            return redirect(TASK_DETAIL, pk=task.pk)

        messages.error(request, "입력값을 확인해주세요.")
    else:
        form = TaskForm(instance=task)

    return render(request, "board/task_edit.html", {
        "form": form,
        "task": task,
        "attachments": task.attachments.all(),
    })


# =========================================================
# ✅ Post (업무요청) — superuser/head/leader
# =========================================================
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def post_list(request: HttpRequest) -> HttpResponse:
    is_superuser = (getattr(request.user, "grade", "") == "superuser")
    p = _read_list_params(request)

    qs = (
        Post.objects
        .annotate(comment_count=Count("comments", distinct=True))
        .order_by("-created_at")
    )

    qs = _apply_keyword_filter(
        qs, p.keyword, p.search_type,
        title_field="title",
        content_field="content",
        user_name_field="user_name",
    )
    qs = _apply_common_list_filters(
        qs,
        date_from=p.date_from,
        date_to=p.date_to,
        selected_category=p.selected_category,
        selected_handler=p.selected_handler,
        selected_status=p.selected_status,
    )

    posts, per_page = _paginate(request, qs, default_per_page=10)
    query_string = _build_query_string_without_page(request)

    return render(request, "board/post_list.html", {
        "posts": posts,
        "per_page": per_page,
        "per_page_choices": PER_PAGE_CHOICES,
        "query_string": query_string,

        "is_superuser": is_superuser,
        "handlers": _get_handlers(),
        "status_choices": STATUS_CHOICES,

        "keyword": p.keyword,
        "search_type": p.search_type,
        "selected_handler": p.selected_handler,
        "selected_status": p.selected_status,

        "category_choices": POST_CATEGORY_VALUES,
        "selected_category": p.selected_category,

        "date_from": p.date_from_raw,
        "date_to": p.date_to_raw,
    })


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
@require_POST
def ajax_update_post_field(request: HttpRequest) -> JsonResponse:
    """인라인 변경은 superuser만 허용(기존 정책 유지)"""
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    post_id = request.POST.get("post_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or request.POST.get(action) or "").strip()

    if not post_id or action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, id=post_id)
    return _inline_update_common(obj=post, action=action, value=value, allowed_status_values=STATUS_CHOICES)


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
@require_POST
def ajax_update_post_field_detail(request: HttpRequest, pk: int) -> JsonResponse:
    """상세 페이지 인라인 변경(superuser only)"""
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, pk=pk)
    return _inline_update_common(obj=post, action=action, value=value, allowed_status_values=STATUS_CHOICES)


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def post_detail(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (getattr(request.user, "grade", "") == "superuser")

    # 정책: 수정/삭제는 superuser만(안전)
    can_edit = is_superuser

    if request.method == "POST":
        act = (request.POST.get("action_type") or "").strip()

        handled = _handle_comments_actions(
            request=request,
            obj=post,
            comment_model=Comment,
            fk_field="post",
            redirect_detail_name=POST_DETAIL,
        )
        if handled:
            return handled

        if act == "delete_post":
            if not can_edit:
                messages.error(request, "삭제 권한이 없습니다.")
                return redirect(POST_DETAIL, pk=pk)
            post.delete()
            messages.success(request, "게시글이 삭제되었습니다.")
            return redirect(POST_LIST)

        return redirect(POST_DETAIL, pk=pk)

    post_info = {
        "소속(요청자)": post.user_branch,
        "성명(요청자)": post.user_name,
        "사번(요청자)": post.user_id,
    }

    return render(request, "board/post_detail.html", {
        "post": post,
        "post_info": post_info,
        "is_superuser": is_superuser,
        "can_edit": can_edit,

        "handlers": _get_handlers(),
        "status_choices": STATUS_CHOICES,

        "comments": post.comments.order_by("-created_at"),
        "attachments": post.attachments.all(),
        "form": CommentForm(),

        "detail_url": reverse(POST_DETAIL, kwargs={"pk": post.pk}),
        "list_url": reverse(POST_LIST),
        "edit_url": reverse(POST_EDIT, kwargs={"pk": post.pk}),
    })


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def post_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user_id = str(request.user.id)
            post.user_name = getattr(request.user, "name", "") or ""
            post.user_branch = getattr(request.user, "branch", "") or ""
            post.save()

            files = request.FILES.getlist("attachments")

            def _create_post_attachment(**kwargs):
                return Attachment.objects.create(post=post, **kwargs)

            _save_attachments(files=files, create_func=_create_post_attachment)

            messages.success(request, "게시글이 등록되었습니다.")
            return redirect(POST_DETAIL, pk=post.pk)

        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = PostForm()

    return render(request, "board/post_create.html", {"form": form})


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def post_edit(request: HttpRequest, pk: int) -> HttpResponse:
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (getattr(request.user, "grade", "") == "superuser")

    if not is_superuser:
        messages.error(request, "수정 권한이 없습니다.")
        return redirect(POST_DETAIL, pk=pk)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()

            del_ids = request.POST.getlist("delete_files")
            if del_ids:
                Attachment.objects.filter(id__in=del_ids, post=post).delete()

            files = request.FILES.getlist("attachments")

            def _create_post_attachment(**kwargs):
                return Attachment.objects.create(post=post, **kwargs)

            _save_attachments(files=files, create_func=_create_post_attachment)

            messages.success(request, "게시글이 수정되었습니다.")
            return redirect(POST_DETAIL, pk=post.pk)

        messages.error(request, "입력값을 확인해주세요.")
    else:
        form = PostForm(instance=post)

    return render(request, "board/post_edit.html", {
        "form": form,
        "post": post,
        "attachments": post.attachments.all(),
    })


# =========================================================
# 📘 Support / States Form — superuser/head/leader
# =========================================================
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def support_form(request: HttpRequest) -> HttpResponse:
    """
    업무요청서 작성 페이지
    Policy: superuser / head / leader
    """
    return render(request, "board/support_form.html", _build_support_form_context())


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def states_form(request: HttpRequest) -> HttpResponse:
    """
    소명서 작성 페이지
    Policy: superuser / head / leader
    Notes: 현재 템플릿은 contracts만 사용하지만 컨텍스트는 SSOT로 통일
    """
    return render(request, "board/states_form.html", _build_support_form_context())


# =========================================================
# 🔍 Search User — superuser/head/leader
# =========================================================
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def search_user(request: HttpRequest) -> JsonResponse:
    """
    Legacy alias: /board/search-user/
    실제 구현은 accounts.search_api.search_users_for_api(SSOT)
    """
    return JsonResponse(search_users_for_api(request))


# =========================================================
# 🧾 PDF Generate — superuser/head/leader
# =========================================================
@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def generate_request_support(request: HttpRequest) -> HttpResponse:
    pdf_response = build_support(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect(SUPPORT_FORM)
    return pdf_response


@login_required
@grade_required(*BOARD_ALLOWED_GRADES)
def generate_request_states(request: HttpRequest) -> HttpResponse:
    pdf_response = build_states(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect(STATES_FORM)
    return pdf_response
