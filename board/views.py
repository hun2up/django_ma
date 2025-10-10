from django.shortcuts import render, redirect, get_object_or_404
from .models import Post

def post_list(request):
    posts = Post.objects.order_by('-created_at')
    return render(request, 'board/post_list.html', {'posts': posts})

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'board/post_detail.html', {'post': post})

def post_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')

        if title and content:
            Post.objects.create(title=title, content=content)
            return redirect('post_list')
        else:
            error = "제목과 내용을 모두 입력하세요."
            return render(request, 'board/post_create.html', {'error': error})

    return render(request, 'board/post_create.html')
