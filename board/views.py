# django_ma/board/views.py
# ===========================================
# 📂 board/views.py — 업무요청/직원업무 게시판 + PDF (REFAC)
# - 목표: 가독성/유지보수 향상 (공통 모듈화)
# - 기존 기능/동작 유지 (컨텍스트 키, URL, 권한, 메시지)
# ===========================================

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Iterable

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, QuerySet
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .forms import PostForm, CommentForm, TaskForm, TaskCommentForm
from .models import (
    Post, Attachment, Comment,
    Task, TaskAttachment, TaskComment, TASK_STATUS_CHOICES,
)

from board.utils.pdf_support_utils import generate_request_support as build_support
from board.utils.pdf_states_utils import generate_request_states as build_states

logger = logging.getLogger("board.access")
User = get_user_model()

# -------------------------
# Constants
# -------------------------
STATUS_CHOICES = ["확인중", "진행중", "보완요청", "완료", "반려"]
TASK_STATUS_VALUES = [s[0] for s in TASK_STATUS_CHOICES]

POST_CATEGORY_VALUES = ["위해촉", "리스크/유지율", "수수료/채권", "운영자금", "전산", "기타"]
TASK_CATEGORY_VALUES = ["위해촉", "리스크/유지율", "수수료/채권", "운영자금", "전산", "기타", "민원", "신규제휴"]

PER_PAGE_CHOICES = [10, 25, 50, 100]

INLINE_ACTIONS = ("handler", "status")


# =========================================================
# ✅ 공용 유틸 (GET/필터/페이지네이션)
# =========================================================
def _get_handlers() -> list[str]:
    return list(User.objects.filter(grade="superuser").values_list("name", flat=True))


def _get_per_page(request, default=10) -> int:
    raw = str(request.GET.get("per_page", "")).strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return n if n in PER_PAGE_CHOICES else default


def _build_query_string_without_page(request) -> str:
    q = request.GET.copy()
    if "page" in q:
        q.pop("page")
    return q.urlencode()


def _parse_date_range(request) -> Tuple[str, str, Optional[Any], Optional[Any]]:
    """
    returns: (date_from_raw, date_to_raw, date_from(date|None), date_to(date|None))
    """
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    return date_from_raw, date_to_raw, date_from, date_to


def _apply_keyword_filter(qs: QuerySet, keyword: str, search_type: str, *, title_field: str, content_field: str, user_name_field: str) -> QuerySet:
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

    # fallback(안전)
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
    # 접수일자
    if date_from:
        qs = qs.filter(**{f"{created_field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{created_field}__date__lte": date_to})

    # 구분
    if selected_category and selected_category != "전체":
        qs = qs.filter(**{f"{category_field}__iexact": selected_category})

    # 담당자
    if selected_handler != "전체":
        qs = qs.filter(**{handler_field: selected_handler})

    # 상태
    if selected_status != "전체":
        qs = qs.filter(**{status_field: selected_status})

    return qs


def _paginate(request, qs: QuerySet, *, default_per_page=10):
    per_page = _get_per_page(request, default=default_per_page)
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
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


def _read_list_params(request) -> ListParams:
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
# ✅ 공용 유틸 (댓글/첨부/인라인 업데이트)
# =========================================================
def _handle_comments_actions(*, request, obj, comment_model, fk_field: str, redirect_detail_name: str):
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


def _save_attachments(*, files: Iterable, create_func):
    """
    files: request.FILES.getlist("attachments")
    create_func: callable(file=f, original_name=..., size=..., content_type=...)
      - Post: Attachment.objects.create(post=post, ...)
      - Task: TaskAttachment.objects.create(task=task, ...)
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
    request,
    obj,
    obj_label: str,
    id_value: str,
    action: str,
    value: str,
    allowed_status_values: list[str],
) -> JsonResponse:
    """
    obj: Post or Task
    obj_label: "게시글" 같은 표시용(현재는 메시지 그대로 유지)
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

    # status
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
# ✅ 직원업무 게시판
# =========================================================
@grade_required("superuser")
@login_required
def task_list(request):
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


@require_POST
@grade_required("superuser")
@login_required
def ajax_update_task_field(request):
    task_id = request.POST.get("task_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or request.POST.get(action) or "").strip()

    if not task_id or action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, id=task_id)
    return _inline_update_common(
        request=request,
        obj=task,
        obj_label="직원업무",
        id_value=str(task_id),
        action=action,
        value=value,
        allowed_status_values=TASK_STATUS_VALUES,
    )


@require_POST
@grade_required("superuser")
@login_required
def ajax_update_task_field_detail(request, pk):
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, pk=pk)
    return _inline_update_common(
        request=request,
        obj=task,
        obj_label="직원업무",
        id_value=str(pk),
        action=action,
        value=value,
        allowed_status_values=TASK_STATUS_VALUES,
    )


@grade_required("superuser")
@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    is_superuser = True
    can_edit = True

    if request.method == "POST":
        act = (request.POST.get("action_type") or "").strip()

        handled = _handle_comments_actions(
            request=request,
            obj=task,
            comment_model=TaskComment,
            fk_field="task",
            redirect_detail_name="task_detail",
        )
        if handled:
            return handled

        if act == "delete_task":
            task.delete()
            messages.success(request, "게시글이 삭제되었습니다.")
            return redirect("task_list")

        return redirect("task_detail", pk=pk)

    task_info = {
        "소속(요청자)": task.user_branch,
        "성명(요청자)": task.user_name,
        "사번(요청자)": task.user_id,
    }

    return render(request, "board/task_detail.html", {
        "task": task,
        "task_info": task_info,
        "is_superuser": is_superuser,
        "can_edit": can_edit,
        "handlers": _get_handlers(),
        "comments": task.comments.order_by("-created_at"),
        "attachments": task.attachments.all(),
        "form": TaskCommentForm(),
        "detail_url": reverse("task_detail", kwargs={"pk": task.pk}),
        "list_url": reverse("task_list"),
        "edit_url": reverse("task_edit", kwargs={"pk": task.pk}),
        "status_choices": TASK_STATUS_VALUES,
    })


@grade_required("superuser")
@login_required
def task_create(request):
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
            return redirect("task_detail", pk=task.pk)

        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = TaskForm()

    return render(request, "board/task_create.html", {"form": form})


@grade_required("superuser")
@login_required
def task_edit(request, pk):
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
            return redirect("task_detail", pk=task.pk)

        messages.error(request, "입력값을 확인해주세요.")
    else:
        form = TaskForm(instance=task)

    return render(request, "board/task_edit.html", {
        "form": form,
        "task": task,
        "attachments": task.attachments.all(),
    })


# =========================================================
# ✅ 업무요청 게시판
# =========================================================
@login_required
def post_list(request):
    is_superuser = (request.user.grade == "superuser")
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


@require_POST
@login_required
def ajax_update_post_field(request):
    if request.user.grade != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    post_id = request.POST.get("post_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or request.POST.get(action) or "").strip()

    if not post_id or action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, id=post_id)
    return _inline_update_common(
        request=request,
        obj=post,
        obj_label="업무요청",
        id_value=str(post_id),
        action=action,
        value=value,
        allowed_status_values=STATUS_CHOICES,
    )


@require_POST
@login_required
def ajax_update_post_field_detail(request, pk):
    if request.user.grade != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in INLINE_ACTIONS:
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, pk=pk)
    return _inline_update_common(
        request=request,
        obj=post,
        obj_label="업무요청",
        id_value=str(pk),
        action=action,
        value=value,
        allowed_status_values=STATUS_CHOICES,
    )


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    if not is_superuser and str(request.user.id) != str(post.user_id):
        messages.error(request, "조회 권한이 없습니다.")
        return redirect("post_list")

    can_edit = is_superuser or (str(request.user.id) == str(post.user_id))

    if request.method == "POST":
        act = (request.POST.get("action_type") or "").strip()

        handled = _handle_comments_actions(
            request=request,
            obj=post,
            comment_model=Comment,
            fk_field="post",
            redirect_detail_name="post_detail",
        )
        if handled:
            return handled

        if act == "delete_post":
            if not can_edit:
                messages.error(request, "삭제 권한이 없습니다.")
                return redirect("post_detail", pk=pk)
            post.delete()
            messages.success(request, "게시글이 삭제되었습니다.")
            return redirect("post_list")

        return redirect("post_detail", pk=pk)

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
        "detail_url": reverse("post_detail", kwargs={"pk": post.pk}),
        "list_url": reverse("post_list"),
        "edit_url": reverse("post_edit", kwargs={"pk": post.pk}),
    })


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user_id = request.user.id
            post.user_name = getattr(request.user, "name", "") or ""
            post.user_branch = getattr(request.user, "branch", "") or ""
            post.save()

            files = request.FILES.getlist("attachments")

            def _create_post_attachment(**kwargs):
                return Attachment.objects.create(post=post, **kwargs)

            _save_attachments(files=files, create_func=_create_post_attachment)

            messages.success(request, "게시글이 등록되었습니다.")
            return redirect("post_detail", pk=post.pk)

        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = PostForm()

    return render(request, "board/post_create.html", {"form": form})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    if not (is_superuser or str(request.user.id) == str(post.user_id)):
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("post_detail", pk=pk)

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
            return redirect("post_detail", pk=post.pk)

        messages.error(request, "입력값을 확인해주세요.")
    else:
        form = PostForm(instance=post)

    return render(request, "board/post_edit.html", {
        "form": form,
        "post": post,
        "attachments": post.attachments.all(),
    })


# =========================================================
# 📘 업무요청서/소명서 폼
# =========================================================
@login_required
@grade_required(["superuser", "main_admin", "sub_admin", "basic"])
def support_form(request):
    fields = [("성명", "target_name_"), ("사번", "target_code_"), ("입사일", "target_join_"), ("퇴사일", "target_leave_")]
    contracts = [("보험사", "insurer_", 3), ("증권번호", "policy_no_", 3), ("계약자(피보험자)", "contractor_", 3), ("보험료", "premium_", 2)]
    return render(request, "board/support_form.html", {"fields": fields, "contracts": contracts})


@login_required
@grade_required(["superuser", "main_admin", "sub_admin", "basic"])
def states_form(request):
    fields = [("성명", "target_name_"), ("사번", "target_code_"), ("입사일", "target_join_"), ("퇴사일", "target_leave_")]
    contracts = [("보험사", "insurer_", 3), ("증권번호", "policy_no_", 3), ("계약자(피보험자)", "contractor_", 3), ("보험료", "premium_", 2)]
    return render(request, "board/states_form.html", {"fields": fields, "contracts": contracts})


# =========================================================
# 🔍 대상자 검색
# =========================================================
@login_required
def search_user(request):
    keyword = request.GET.get("q", "").strip()
    if not keyword:
        return JsonResponse({"results": []})

    qs = CustomUser.objects.all()
    if request.user.grade != "superuser":
        qs = qs.filter(branch=request.user.branch)

    users = (
        qs.filter(Q(name__icontains=keyword) | Q(id__icontains=keyword))
        .values("id", "name", "regist", "branch", "enter", "quit")[:20]
    )
    return JsonResponse({"results": list(users)})


# =========================================================
# 🧾 PDF 생성
# =========================================================
@login_required
def generate_request_support(request):
    pdf_response = build_support(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect("support_form")
    return pdf_response


@login_required
def generate_request_states(request):
    pdf_response = build_states(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect("states_form")
    return pdf_response
