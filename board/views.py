# django_ma/board/views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from .models import Post
from .forms import PostForm  # ✅ 폼 불러오기

# ✅ CustomUser 모델 참조 (User = get_user_model()는 함수 밖에 선언)
User = get_user_model()

# 📋 게시글 목록 보기 + 상태/담당자 변경 기능 포함
@login_required
def post_list(request):
    post_list = Post.objects.order_by('-created_at')
    paginator = Paginator(post_list, 10)
    page = request.GET.get('page')
    posts = paginator.get_page(page)

    User = get_user_model()
    is_superuser = (request.user.grade == "superuser")
    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']

    # ✅ 담당자/상태 변경 처리 (슈퍼유저만 가능)
    if request.method == "POST" and is_superuser:
        post_id = request.POST.get("post_id")
        action_type = request.POST.get("action_type")
        post = get_object_or_404(Post, id=post_id)

        if action_type == "handler":
            handler_name = request.POST.get("handler", "").strip()
            post.handler = "" if handler_name in ["", "선택"] else handler_name
            post.save()
            messages.success(request, f"[{post.title}] 담당자가 변경되었습니다.")

        elif action_type == "status":
            status_value = request.POST.get("status", "").strip()
            post.status = status_value if status_value else "확인중"
            post.save()
            messages.success(request, f"[{post.title}] 상태가 변경되었습니다.")

        return redirect("post_list")

    return render(request, 'board/post_list.html', {
        'posts': posts,
        'is_superuser': is_superuser,
        'handlers': handlers,
        'status_choices': status_choices,
    })


@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    if request.method == "POST" and is_superuser:
        action_type = request.POST.get("action_type")

        # ✅ 담당자 변경
        if action_type == "handler":
            handler_name = request.POST.get("handler", "").strip()
            post.handler = "" if handler_name in ["", "선택"] else handler_name
            post.save()
            messages.success(request, "담당자가 변경되었습니다.")  # ✅ 안내 메시지 추가
            print(f"[DEBUG] Handler updated to: {post.handler}")

        # ✅ 상태 변경
        elif action_type == "status":
            status_value = request.POST.get("status", "").strip()
            post.status = status_value if status_value else "확인중"
            post.save()
            messages.success(request, "상태가 변경되었습니다.")  # ✅ 안내 메시지 추가
            print(f"[DEBUG] Status updated to: {post.status}")

        return redirect("post_detail", pk=pk)

    # 담당자 목록: grade='superuser' 사용자 이름만
    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']

    return render(request, "board/post_detail.html", {
        "post": post,
        "is_superuser": is_superuser,
        "handlers": handlers,
        "status_choices": status_choices,
    })

# 📝 게시글 작성
@login_required
def post_create(request):
    """
    - GET 요청 → 빈 폼 표시
    - POST 요청 → 입력 데이터 검증 후 저장
    - 로그인한 사용자 정보(id, name, branch)를 게시글에 자동 저장
    """
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)  # 저장을 미루고...

            # ✅ 로그인한 사용자 정보 추가
            post.user_id = request.user.id
            post.user_name = request.user.name
            post.user_branch = request.user.branch

            post.save()  # 실제 저장
            return redirect('post_list')

        # ❌ 유효성 실패 시
        return render(request, 'board/post_create.html', {'form': form})

    else:
        form = PostForm()
        return render(request, 'board/post_create.html', {'form': form})

