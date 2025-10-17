# django_ma/board/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import PostForm
from .models import Post, Attachment


# ✅ 전역에서 한 번만 로드
User = get_user_model()


# -----------------------------------------------------------------------------
# 📋 게시글 목록
# -----------------------------------------------------------------------------
@login_required
def post_list(request):
    """
    게시글 목록 + (슈퍼유저용) 담당자/상태 변경 기능
    """
    posts_qs = Post.objects.order_by('-created_at')
    paginator = Paginator(posts_qs, 10)
    posts = paginator.get_page(request.GET.get('page'))

    is_superuser = (request.user.grade == "superuser")
    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']

    # ✅ 담당자 / 상태 변경 처리 (슈퍼유저 전용)
    if request.method == "POST" and is_superuser:
        post = get_object_or_404(Post, id=request.POST.get("post_id"))
        action_type = request.POST.get("action_type")

        if action_type == "handler":
            handler_name = request.POST.get("handler", "").strip()
            post.handler = "" if handler_name in ["", "선택"] else handler_name
            post.save()
            messages.success(request, f"[{post.title}] 담당자가 '{post.handler or '미지정'}'으로 변경되었습니다.")

        elif action_type == "status":
            status_value = request.POST.get("status", "").strip()
            post.status = status_value or "확인중"
            post.save()
            messages.success(request, f"[{post.title}] 상태가 '{post.status}'로 변경되었습니다.")

        return redirect("post_list")

    return render(request, "board/post_list.html", {
        "posts": posts,
        "is_superuser": is_superuser,
        "handlers": handlers,
        "status_choices": status_choices,
    })


# -----------------------------------------------------------------------------
# 📄 게시글 상세
# -----------------------------------------------------------------------------
@login_required
def post_detail(request, pk):
    """
    게시글 상세 보기 + (슈퍼유저용) 상태/담당자 변경 + 첨부파일 목록 표시
    """
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    if request.method == "POST" and is_superuser:
        action_type = request.POST.get("action_type")

        if action_type == "handler":
            handler_name = request.POST.get("handler", "").strip()
            post.handler = "" if handler_name in ["", "선택"] else handler_name
            post.save()
            messages.success(request, f"담당자가 '{post.handler or '미지정'}'으로 변경되었습니다.")

        elif action_type == "status":
            status_value = request.POST.get("status", "").strip()
            post.status = status_value or "확인중"
            post.save()
            messages.success(request, f"상태가 '{post.status}'로 변경되었습니다.")

        return redirect("post_detail", pk=pk)

    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']

    return render(request, "board/post_detail.html", {
        "post": post,
        "is_superuser": is_superuser,
        "handlers": handlers,
        "status_choices": status_choices,
    })


# -----------------------------------------------------------------------------
# 📝 게시글 작성
# -----------------------------------------------------------------------------
@login_required
def post_create(request):
    """
    게시글 작성
    - 로그인 사용자 정보 자동 추가
    - 여러 첨부파일 업로드 가능
    """
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)
            post.user_id = request.user.id
            post.user_name = getattr(request.user, "name", "")
            post.user_branch = getattr(request.user, "branch", "")
            post.save()

            # ✅ 첨부파일 저장
            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(
                    post=post,
                    file=f,
                    original_name=f.name,
                    size=getattr(f, "size", 0),
                    content_type=getattr(f, "content_type", "") or "",
                )

            messages.success(request, "게시글이 성공적으로 등록되었습니다.")
            return redirect("post_detail", pk=post.pk)

        # ❌ 폼 검증 실패
        messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = PostForm()

    return render(request, "board/post_create.html", {"form": form})


# -----------------------------------------------------------------------------
# 📝 게시글 수정
# -----------------------------------------------------------------------------
@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    # ✅ 본인 글 또는 관리자만 수정 가능
    if request.user.id != post.user_id and not is_superuser:
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("post_detail", pk=post.pk)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)

        # ✅ 1. 첨부파일 삭제 처리
        delete_files = request.POST.getlist("delete_files")
        if delete_files:
            Attachment.objects.filter(id__in=delete_files, post=post).delete()

        # ✅ 2. 게시글 수정 및 새 첨부파일 추가 처리
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.user_id = request.user.id
            updated_post.user_name = getattr(request.user, "name", "")
            updated_post.user_branch = getattr(request.user, "branch", "")
            updated_post.save()

            # ✅ 새 첨부파일 추가 저장
            for f in request.FILES.getlist("attachments"):
                Attachment.objects.create(
                    post=post,
                    file=f,
                    original_name=f.name,
                    size=getattr(f, "size", 0),
                    content_type=getattr(f, "content_type", "") or "",
                )

            messages.success(request, "게시글이 성공적으로 수정되었습니다.")
            return redirect("post_detail", pk=post.pk)
        else:
            messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = PostForm(instance=post)

    # ✅ 첨부파일 목록을 같이 전달
    attachments = post.attachments.all()

    return render(request, "board/post_edit.html", {
        "form": form,
        "post": post,
        "attachments": attachments,
    })