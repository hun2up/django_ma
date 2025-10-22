# ===========================================
# 📂 board/views.py — 업무요청 게시판 & PDF 생성 뷰
# ===========================================

import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import CustomUser
from .forms import PostForm, CommentForm
from .models import Post, Attachment, Comment
from board.utils.pdf_utils import generate_request_pdf as build_pdf

# ===========================================
# 🔧 기본 설정 / 상수
# ===========================================
logger = logging.getLogger("board.access")
User = get_user_model()

STATUS_CHOICES = ["확인중", "진행중", "보완요청", "완료", "반려"]

# ===========================================
# 📋 게시글 목록 (검색 + 필터)
# ===========================================
@login_required
def post_list(request):
    """
    게시글 목록
    - 제목, 내용, 작성자, 상태, 담당자별 검색/필터
    - 슈퍼유저: 상태·담당자 수정 가능
    """
    posts_qs = Post.objects.order_by("-created_at")
    is_superuser = request.user.grade == "superuser"

    # 🔸 검색 파라미터
    keyword = request.GET.get("keyword", "").strip()
    search_type = request.GET.get("search_type", "title")
    selected_handler = request.GET.get("handler", "전체")
    selected_status = request.GET.get("status", "전체")

    # 🔸 검색 조건
    if keyword:
        match search_type:
            case "title":
                posts_qs = posts_qs.filter(title__icontains=keyword)
            case "content":
                posts_qs = posts_qs.filter(content__icontains=keyword)
            case "title_content":
                posts_qs = posts_qs.filter(Q(title__icontains=keyword) | Q(content__icontains=keyword))
            case "user_name":
                posts_qs = posts_qs.filter(user_name__icontains=keyword)
            case "category":
                posts_qs = posts_qs.filter(category__icontains=keyword)

    # 🔸 필터링
    if selected_handler != "전체":
        posts_qs = posts_qs.filter(handler=selected_handler)
    if selected_status != "전체":
        posts_qs = posts_qs.filter(status=selected_status)

    # 🔸 페이지네이션
    posts = Paginator(posts_qs, 10).get_page(request.GET.get("page"))

    # 🔸 상태/담당자 변경 (슈퍼유저 전용)
    if request.method == "POST" and is_superuser:
        post = get_object_or_404(Post, id=request.POST.get("post_id"))
        action = request.POST.get("action_type")

        if action == "handler":
            new_handler = request.POST.get("handler", "").strip() or ""
            post.handler = None if new_handler in ["", "선택"] else new_handler
            post.save()
            messages.success(request, f"담당자 → '{post.handler or '미지정'}'로 변경되었습니다.")
        elif action == "status":
            new_status = request.POST.get("status", "").strip() or "확인중"
            post.status = new_status
            post.save()
            messages.success(request, f"상태 → '{post.status}'로 변경되었습니다.")
        return redirect("post_list")

    return render(request, "board/post_list.html", {
        "posts": posts,
        "is_superuser": is_superuser,
        "handlers": list(User.objects.filter(grade="superuser").values_list("name", flat=True)),
        "status_choices": STATUS_CHOICES,
        "keyword": keyword,
        "selected_handler": selected_handler,
        "selected_status": selected_status,
    })


# ===========================================
# 📄 게시글 상세 + 댓글 CRUD
# ===========================================
@login_required
def post_detail(request, pk):
    """게시글 상세 — 댓글/첨부/상태/담당자 관리"""
    post = get_object_or_404(Post, pk=pk)
    is_superuser = request.user.grade == "superuser"

    # 🔸 권한 확인
    if not is_superuser and str(request.user.id) != str(post.user_id):
        messages.error(request, "조회 권한이 없습니다.")
        return redirect("post_list")

    # 🔸 담당자/상태 변경
    def update_post_field(field_name):
        """담당자/상태 갱신 헬퍼"""
        if not is_superuser:
            messages.error(request, "권한이 없습니다.")
            return
        value = request.POST.get(field_name, "").strip() or None
        setattr(post, field_name, value)
        post.save()
        messages.success(request, f"{field_name} 변경 완료")

    # 🔸 POST 요청 처리
    if request.method == "POST":
        act = request.POST.get("action_type")
        match act:
            case "handler" | "status":
                update_post_field(act)
            case "comment":
                Comment.objects.create(
                    post=post, author=request.user, content=request.POST.get("content", "")
                )
                messages.success(request, "댓글 등록 완료")
            case "edit_comment":
                c = get_object_or_404(Comment, id=request.POST["comment_id"], author=request.user)
                c.content = request.POST.get("content", "").strip()
                c.save()
                messages.success(request, "댓글 수정 완료")
            case "delete_comment":
                Comment.objects.filter(id=request.POST["comment_id"], author=request.user).delete()
                messages.info(request, "댓글 삭제 완료")
        return redirect("post_detail", pk=pk)

    # 🔸 템플릿 전달용 정보
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
    """게시글 작성 — 사용자 자동 입력 + 첨부파일 등록"""
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user_id = request.user.id
            post.user_name = request.user.name
            post.user_branch = request.user.branch
            post.save()

            # 첨부파일 등록
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
    """게시글 수정 — 본인 또는 슈퍼유저만 가능"""
    post = get_object_or_404(Post, pk=pk)
    is_superuser = request.user.grade == "superuser"

    if not (is_superuser or request.user.id == post.user_id):
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("post_detail", pk=pk)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()

            # 첨부파일 삭제 및 추가
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

    return render(
        request,
        "board/post_edit.html",
        {"form": form, "post": post, "attachments": post.attachments.all()},
    )


# ===========================================
# 📘 참고 문서 페이지
# ===========================================
@login_required
def support_form(request):
    """업무요청서 작성 페이지"""
    fields = [
        ("성명", "target_name_"),
        ("사번", "target_code_"),
        ("입사일", "target_join_"),
        ("퇴사일", "target_leave_"),
    ]
    contracts = [
        ("보험사", "insurer_", 2),
        ("증권번호", "policy_no_", 3),
        ("계약자(피보험자)", "contractor_", 3),
        ("보험료", "premium_", 3),
    ]
    return render(request, "board/support_form.html", {
        "fields": fields,
        "contracts": contracts,
    })


# ===========================================
# 🔍 대상자 검색
# ===========================================
@login_required
def search_user(request):
    """대상자 검색 — 일반 사용자는 자신의 지점(branch)만 조회"""
    keyword = request.GET.get("q", "").strip()
    if not keyword:
        return JsonResponse({"results": []})

    qs = CustomUser.objects.all()
    if request.user.grade != "superuser":
        qs = qs.filter(branch=request.user.branch)

    users = qs.filter(
        Q(name__icontains=keyword) | Q(regist__icontains=keyword)
    ).values("id", "name", "regist", "branch", "enter", "quit")[:20]

    return JsonResponse({"results": list(users)})


# ===========================================
# 🧾 업무요청서 PDF 생성
# ===========================================
@login_required
def generate_request_pdf(request):
    """PDF 생성 요청 → board.utils.pdf_utils 호출"""
    pdf_response = build_pdf(request)
    if pdf_response is None:
        messages.error(request, "PDF 생성 중 오류가 발생했습니다.")
        return redirect("support_form")
    return pdf_response
