# django_ma/board/views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import Post
from .forms import PostForm  # ✅ 폼 불러오기


# 📋 게시글 목록 보기
@login_required
def post_list(request):
    post_list = Post.objects.order_by('-created_at')
    paginator = Paginator(post_list, 10)  # 페이지당 10개 표시
    page = request.GET.get('page')
    posts = paginator.get_page(page)
    return render(request, 'board/post_list.html', {'posts': posts})


# 🔍 게시글 상세 보기
@login_required
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'board/post_detail.html', {'post': post})


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

