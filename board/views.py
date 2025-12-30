# ===========================================
# 📂 board/views.py — 업무요청 게시판 & PDF 생성 뷰 (Refactor)
# ===========================================

import logging
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from .forms import PostForm, CommentForm
from .models import Post, Attachment, Comment
from board.utils.pdf_support_utils import generate_request_support as build_support
from board.utils.pdf_states_utils import generate_request_states as build_states

logger = logging.getLogger("board.access")
User = get_user_model()

STATUS_CHOICES = ["확인중", "진행중", "보완요청", "완료", "반려"]


# ===========================================
# 📋 결재관리
# ===========================================
@grade_required(["superuser"])
@login_required
def manage_sign(request):
    return render(request, "board/manage_sign.html")


# ===========================================
# 📋 게시글 목록 (검색 + 필터)  ✅ GET 전용
# ===========================================
@login_required
def post_list(request):
    """
    게시글 목록
    - 제목/내용/요청자/구분 검색 + 담당자/상태 필터
    - superuser: 담당자/상태 인라인 변경은 ajax_update_post_field에서 처리
    """
    is_superuser = (request.user.grade == "superuser")

    # GET 파라미터
    keyword = request.GET.get("keyword", "").strip()
    search_type = request.GET.get("search_type", "title")
    selected_handler = request.GET.get("handler", "전체")
    selected_status = request.GET.get("status", "전체")
    page = request.GET.get("page")

    posts_qs = Post.objects.order_by("-created_at")

    # 검색
    if keyword:
        if search_type == "title":
            posts_qs = posts_qs.filter(title__icontains=keyword)
        elif search_type == "content":
            posts_qs = posts_qs.filter(content__icontains=keyword)
        elif search_type == "title_content":
            posts_qs = posts_qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
        elif search_type == "user_name":
            posts_qs = posts_qs.filter(user_name__icontains=keyword)
        elif search_type == "category":
            posts_qs = posts_qs.filter(category__icontains=keyword)

    # 필터
    if selected_handler != "전체":
        posts_qs = posts_qs.filter(handler=selected_handler)
    if selected_status != "전체":
        posts_qs = posts_qs.filter(status=selected_status)

    posts = Paginator(posts_qs, 10).get_page(page)
    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))

    return render(request, "board/post_list.html", {
        "posts": posts,
        "is_superuser": is_superuser,
        "handlers": handlers,
        "status_choices": STATUS_CHOICES,

        # 유지
        "keyword": keyword,
        "search_type": search_type,
        "selected_handler": selected_handler,
        "selected_status": selected_status,
    })


# ===========================================
# ✅ AJAX: 담당자/상태 즉시 업데이트
# ===========================================
@require_POST
@login_required
def ajax_update_post_field(request):
    """
    superuser 전용: post_list에서 담당자/상태를 즉시(AJAX) 업데이트
    payload: post_id, action_type(handler|status), value
    """
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
        # ✅ handler는 None 금지 (모델이 CharField)
        post.handler = "" if value in ("", "선택") else value
        post.status_updated_at = now
        post.save(update_fields=["handler", "status_updated_at"])

        return JsonResponse({
            "ok": True,
            "message": f"담당자 → '{post.handler or '미지정'}'로 변경되었습니다.",
            "handler": post.handler,
            "status_updated_at": now.strftime("%Y-%m-%d %H:%M"),
        })

    # action == "status"
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
    """
    superuser 전용: post_detail에서 담당자/상태 즉시 업데이트(AJAX)
    payload: action_type(handler|status), value
    """
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

    # action == "status"
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
# 📄 게시글 상세 + 댓글 CRUD
# ===========================================
@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    is_superuser = request.user.grade == "superuser"

    if not is_superuser and str(request.user.id) != str(post.user_id):
        messages.error(request, "조회 권한이 없습니다.")
        return redirect("post_list")

    def update_post_field(field_name):
        if not is_superuser:
            messages.error(request, "권한이 없습니다.")
            return
        value = request.POST.get(field_name, "").strip() or ""
        setattr(post, field_name, value)
        post.status_updated_at = timezone.localtime()
        post.save()
        messages.success(request, f"{field_name} 변경 완료")

    if request.method == "POST":
        act = request.POST.get("action_type")
        match act:
            case "handler" | "status":
                update_post_field(act)
            case "comment":
                Comment.objects.create(post=post, author=request.user, content=request.POST.get("content", ""))
                messages.success(request, "댓글 등록 완료")
            case "edit_comment":
                c = get_object_or_404(Comment, id=request.POST["comment_id"], author=request.user)
                c.content = request.POST.get("content", "").strip()
                c.save()
                messages.success(request, "댓글 수정 완료")
            case "delete_comment":
                Comment.objects.filter(id=request.POST["comment_id"], author=request.user).delete()
                messages.info(request, "댓글 삭제 완료")
            case "delete_post":
                if not (is_superuser or str(request.user.id) == str(post.user_id)):
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
        "handlers": list(User.objects.filter(grade="superuser").values_list("name", flat=True)),
        "status_choices": STATUS_CHOICES,
        "comments": post.comments.order_by("-created_at"),
        "attachments": post.attachments.all(),
        "form": CommentForm(),
    })


# ===========================================
# 📝 게시글 작성 / 수정
# ===========================================
@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user_id = request.user.id
            post.user_name = request.user.name
            post.user_branch = request.user.branch
            post.save()

            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(
                    post=post,
                    file=f,
                    original_name=f.name,
                    size=getattr(f, "size", 0),
                    content_type=getattr(f, "content_type", ""),
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
    is_superuser = request.user.grade == "superuser"

    if not (is_superuser or request.user.id == post.user_id):
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
                    original_name=f.name,
                    size=f.size,
                    content_type=f.content_type or "",
                )
            messages.success(request, "게시글이 수정되었습니다.")
            return redirect("post_detail", pk=pk)
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
