# django_ma/board/views.py
# ===========================================
# 📂 board/views.py — 업무요청 게시판 & PDF 생성 뷰 (FINAL)
# ===========================================

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .forms import PostForm, CommentForm, TaskForm, TaskCommentForm
from .models import (
    Post, Attachment, Comment,
    Task, TaskAttachment, TaskComment
)

from board.utils.pdf_support_utils import generate_request_support as build_support
from board.utils.pdf_states_utils import generate_request_states as build_states

logger = logging.getLogger("board.access")
User = get_user_model()

STATUS_CHOICES = ["확인중", "진행중", "보완요청", "완료", "반려"]


# =========================================================
# ✅ 공용 유틸
# =========================================================
def _get_handlers():
    return list(User.objects.filter(grade="superuser").values_list("name", flat=True))


def _handle_comments_actions(*, request, obj, comment_model, fk_field: str, redirect_detail_name: str):
    """
    detail 페이지 댓글 공용 처리
    - fk_field: Comment 모델의 FK 필드명 ("post" or "task")
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


# =========================
# ✅ 직원업무 게시판: 목록
# =========================
@grade_required(["superuser"])
@login_required
def task_list(request):
    keyword = request.GET.get("keyword", "").strip()
    search_type = request.GET.get("search_type", "title")
    selected_handler = request.GET.get("handler", "전체")
    selected_status = request.GET.get("status", "전체")
    page = request.GET.get("page")

    qs = Task.objects.order_by("-created_at")

    if keyword:
        if search_type == "title":
            qs = qs.filter(title__icontains=keyword)
        elif search_type == "content":
            qs = qs.filter(content__icontains=keyword)
        elif search_type == "title_content":
            qs = qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
        elif search_type == "user_name":
            qs = qs.filter(user_name__icontains=keyword)
        elif search_type == "category":
            qs = qs.filter(category__icontains=keyword)

    if selected_handler != "전체":
        qs = qs.filter(handler=selected_handler)
    if selected_status != "전체":
        qs = qs.filter(status=selected_status)

    tasks = Paginator(qs, 10).get_page(page)

    return render(request, "board/task_list.html", {
        "tasks": tasks,
        "is_superuser": True,
        "handlers": _get_handlers(),
        "status_choices": STATUS_CHOICES,
        "keyword": keyword,
        "search_type": search_type,
        "selected_handler": selected_handler,
        "selected_status": selected_status,
    })


# =========================
# ✅ 직원업무: 인라인 업데이트 (list)
# =========================
@require_POST
@grade_required(["superuser"])
@login_required
def ajax_update_task_field(request):
    task_id = request.POST.get("task_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if not task_id or action not in ("handler", "status"):
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, id=task_id)
    now = timezone.localtime()

    if action == "handler":
        task.handler = "" if value in ("", "선택") else value
        task.status_updated_at = now
        task.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{task.handler or '미지정'}'로 변경되었습니다.",
            "handler": task.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    if value not in STATUS_CHOICES:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    task.status = value
    task.status_updated_at = now
    task.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{task.status}'로 변경되었습니다.",
        "status": task.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })


# =========================
# ✅ 직원업무: 인라인 업데이트 (detail)
# =========================
@require_POST
@grade_required(["superuser"])
@login_required
def ajax_update_task_field_detail(request, pk):
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in ("handler", "status"):
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    task = get_object_or_404(Task, pk=pk)
    now = timezone.localtime()

    if action == "handler":
        task.handler = "" if value in ("", "선택") else value
        task.status_updated_at = now
        task.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{task.handler or '미지정'}'로 변경되었습니다.",
            "handler": task.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    if value not in STATUS_CHOICES:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    task.status = value
    task.status_updated_at = now
    task.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{task.status}'로 변경되었습니다.",
        "status": task.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })


# =========================
# ✅ 직원업무: 상세
# =========================
@grade_required(["superuser"])
@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    is_superuser = True
    can_edit = True

    if request.method == "POST":
        act = (request.POST.get("action_type") or "").strip()

        # 댓글 처리(공용)
        handled = _handle_comments_actions(
            request=request,
            obj=task,
            comment_model=TaskComment,
            fk_field="task",
            redirect_detail_name="task_detail",
        )
        if handled:
            return handled

        # 삭제
        if act == "delete_task":
            task.delete()
            messages.success(request, "게시글이 삭제되었습니다.")
            return redirect("task_list")

        return redirect("task_detail", pk=pk)

    task_info = {
        "구분": task.category,
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
        "status_choices": STATUS_CHOICES,
        "comments": task.comments.order_by("-created_at"),
        "attachments": task.attachments.all(),

        # include용
        "form": TaskCommentForm(),
        "detail_url": reverse("task_detail", kwargs={"pk": task.pk}),

        # 하단 버튼용
        "list_url": reverse("task_list"),
        "edit_url": reverse("task_edit", kwargs={"pk": task.pk}),
    })


# =========================
# ✅ 직원업무: 작성/수정
# =========================
@grade_required(["superuser"])
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

            for f in request.FILES.getlist("attachments"):
                TaskAttachment.objects.create(
                    task=task,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    size=getattr(f, "size", 0) or 0,
                    content_type=getattr(f, "content_type", "") or "",
                )

            messages.success(request, "게시글이 등록되었습니다.")
            return redirect("task_detail", pk=task.pk)

        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = TaskForm()

    return render(request, "board/task_create.html", {"form": form})


@grade_required(["superuser"])
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

            for f in request.FILES.getlist("attachments"):
                TaskAttachment.objects.create(
                    task=task,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    size=getattr(f, "size", 0) or 0,
                    content_type=getattr(f, "content_type", "") or "",
                )

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


# ===========================================
# 📋 업무요청 게시판: 목록
# ===========================================
@login_required
def post_list(request):
    is_superuser = (request.user.grade == "superuser")

    keyword = request.GET.get("keyword", "").strip()
    search_type = request.GET.get("search_type", "title")
    selected_handler = request.GET.get("handler", "전체")
    selected_status = request.GET.get("status", "전체")
    page = request.GET.get("page")

    qs = Post.objects.order_by("-created_at")

    if keyword:
        if search_type == "title":
            qs = qs.filter(title__icontains=keyword)
        elif search_type == "content":
            qs = qs.filter(content__icontains=keyword)
        elif search_type == "title_content":
            qs = qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
        elif search_type == "user_name":
            qs = qs.filter(user_name__icontains=keyword)
        elif search_type == "category":
            qs = qs.filter(category__icontains=keyword)

    if selected_handler != "전체":
        qs = qs.filter(handler=selected_handler)
    if selected_status != "전체":
        qs = qs.filter(status=selected_status)

    posts = Paginator(qs, 10).get_page(page)

    return render(request, "board/post_list.html", {
        "posts": posts,
        "is_superuser": is_superuser,
        "handlers": _get_handlers(),
        "status_choices": STATUS_CHOICES,
        "keyword": keyword,
        "search_type": search_type,
        "selected_handler": selected_handler,
        "selected_status": selected_status,
    })


# ===========================================
# ✅ 업무요청: 인라인 업데이트(list/detail)
# ===========================================
@require_POST
@login_required
def ajax_update_post_field(request):
    if request.user.grade != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    post_id = request.POST.get("post_id")
    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if not post_id or action not in ("handler", "status"):
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, id=post_id)
    now = timezone.localtime()

    if action == "handler":
        post.handler = "" if value in ("", "선택") else value
        post.status_updated_at = now
        post.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{post.handler or '미지정'}'로 변경되었습니다.",
            "handler": post.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    if value not in STATUS_CHOICES:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    post.status = value
    post.status_updated_at = now
    post.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{post.status}'로 변경되었습니다.",
        "status": post.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })


@require_POST
@login_required
def ajax_update_post_field_detail(request, pk):
    if request.user.grade != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    action = request.POST.get("action_type")
    value = (request.POST.get("value") or "").strip()

    if action not in ("handler", "status"):
        return JsonResponse({"ok": False, "message": "요청이 올바르지 않습니다."}, status=400)

    post = get_object_or_404(Post, pk=pk)
    now = timezone.localtime()

    if action == "handler":
        post.handler = "" if value in ("", "선택") else value
        post.status_updated_at = now
        post.save(update_fields=["handler", "status_updated_at"])
        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{post.handler or '미지정'}'로 변경되었습니다.",
            "handler": post.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    if value not in STATUS_CHOICES:
        return JsonResponse({"ok": False, "message": "상태 값이 올바르지 않습니다."}, status=400)

    post.status = value
    post.status_updated_at = now
    post.save(update_fields=["status", "status_updated_at"])
    return JsonResponse({
        "ok": True,
        "message": f"상태 → '{post.status}'로 변경되었습니다.",
        "status": post.status,
        "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
    })


# ===========================================
# 📄 업무요청: 상세
# ===========================================
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
        "구분": post.category,
        "성명(대상자)": post.fa,
        "사번(대상자)": post.code,
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


# ===========================================
# 📝 업무요청: 작성/수정
# ===========================================
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

            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(
                    post=post,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    size=getattr(f, "size", 0) or 0,
                    content_type=getattr(f, "content_type", "") or "",
                )
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

            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(
                    post=post,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    size=getattr(f, "size", 0) or 0,
                    content_type=getattr(f, "content_type", "") or "",
                )

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


# ===========================================
# 📘 업무요청서/소명서 폼
# ===========================================
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


# ===========================================
# 🔍 대상자 검색
# ===========================================
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


# ===========================================
# 🧾 PDF 생성
# ===========================================
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
