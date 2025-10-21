# django_ma/board/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from accounts.models import CustomUser
from .forms import PostForm, CommentForm
from .models import Post, Attachment, Comment
from datetime import date
from datetime import datetime
from django.http import HttpResponse
from docx import Document
from io import BytesIO
from datetime import date
from reportlab.pdfgen import canvas
from docx2pdf import convert
import os
import tempfile
import subprocess


# ✅ 전역에서 한 번만 로드
User = get_user_model()


# -------------------------------------------------------------------
# 📋 게시글 목록 (검색 + 필터 + 초기화)
# -------------------------------------------------------------------
@login_required
def post_list(request):
    """게시글 목록 + 검색/필터 + (슈퍼유저용) 담당자/상태 변경"""
    posts_qs = Post.objects.order_by('-created_at')
    is_superuser = (request.user.grade == "superuser")

    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']

    # ✅ 검색/필터 파라미터
    search_type = request.GET.get("search_type", "title")
    keyword = request.GET.get("keyword", "").strip()
    selected_handler = request.GET.get("handler", "전체")
    selected_status = request.GET.get("status", "전체")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    date_field = request.GET.get("date_field", "created_at")

    # ✅ 검색 조건
    if keyword:
        if search_type == "title":
            posts_qs = posts_qs.filter(title__icontains=keyword)
        elif search_type == "content":
            posts_qs = posts_qs.filter(content__icontains=keyword)
        elif search_type == "title_content":
            # 🟢 제목 또는 내용에 키워드가 포함된 경우 (OR 검색)
            posts_qs = posts_qs.filter(
                Q(title__icontains=keyword) | Q(content__icontains=keyword)
            )
        elif search_type == "user_name":
            posts_qs = posts_qs.filter(user_name__icontains=keyword)
        elif search_type == "category":
            posts_qs = posts_qs.filter(category__icontains=keyword)

    # ✅ 담당자 필터
    if selected_handler and selected_handler != "전체":
        posts_qs = posts_qs.filter(handler=selected_handler)

    # ✅ 상태 필터
    if selected_status and selected_status != "전체":
        posts_qs = posts_qs.filter(status=selected_status)

    # ✅ 날짜 필터 (created_at 기준)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            posts_qs = posts_qs.filter(created_at__date__gte=start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            posts_qs = posts_qs.filter(created_at__date__lte=end_dt)
        except ValueError:
            pass

    # ✅ 페이지네이션
    paginator = Paginator(posts_qs, 10)
    posts = paginator.get_page(request.GET.get('page'))

    # ✅ 담당자/상태 변경 (슈퍼유저 전용)
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
        "search_type": search_type,
        "keyword": keyword,
        "selected_handler": selected_handler,
        "selected_status": selected_status,
        "date_field": date_field,
    })

# -----------------------------------------------------------------------------
# 📄 게시글 상세 + 댓글 CRUD
# -----------------------------------------------------------------------------
@login_required
def post_detail(request, pk):
    """게시글 상세 보기 + 첨부파일 + (슈퍼유저용 상태/담당자 변경) + 댓글 CRUD"""
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    # ✅ 접근 권한 검사
    if not is_superuser and str(request.user.id) != str(post.user_id):
        messages.error(request, "조회 권한이 없습니다.")
        return redirect("post_list")

    # ──────────────────────────────
    # 🧭 상태 / 담당자 변경 (슈퍼유저)
    # ──────────────────────────────
    if request.method == "POST" and request.POST.get("action_type") in ["handler", "status"]:
        if not is_superuser:
            messages.error(request, "권한이 없습니다.")
            return redirect("post_detail", pk=pk)

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

    # ──────────────────────────────
    # 💬 댓글 등록 / 수정 / 삭제
    # ──────────────────────────────
    if request.method == "POST" and request.POST.get("action_type") in ["comment", "edit_comment", "delete_comment"]:
        action = request.POST.get("action_type")

        # 댓글 등록
        if action == "comment":
            form = CommentForm(request.POST)
            if form.is_valid():
                comment = form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                messages.success(request, "댓글이 등록되었습니다.")
            else:
                messages.error(request, "댓글 내용을 입력해주세요.")
            return redirect("post_detail", pk=pk)

        # 댓글 수정
        elif action == "edit_comment":
            comment_id = request.POST.get("comment_id")
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            new_content = request.POST.get("content", "").strip()
            if new_content:
                comment.content = new_content
                comment.save()
                messages.success(request, "댓글이 수정되었습니다.")
            else:
                messages.error(request, "내용이 비어 있습니다.")
            return redirect("post_detail", pk=pk)

        # 댓글 삭제
        elif action == "delete_comment":
            comment_id = request.POST.get("comment_id")
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            comment.delete()
            messages.info(request, "댓글이 삭제되었습니다.")
            return redirect("post_detail", pk=pk)

    # ──────────────────────────────
    # 📦 렌더링 데이터
    # ──────────────────────────────
    form = CommentForm()
    handlers = list(User.objects.filter(grade="superuser").values_list("name", flat=True))
    status_choices = ['확인중', '진행중', '보완요청', '완료', '반려']
    comments = post.comments.all().order_by('-created_at')
    attachments = post.attachments.all()

    return render(request, "board/post_detail.html", {
        "post": post,
        "is_superuser": is_superuser,
        "handlers": handlers,
        "status_choices": status_choices,
        "comments": comments,
        "attachments": attachments,
        "form": form,
    })


# -----------------------------------------------------------------------------
# 📝 게시글 작성
# -----------------------------------------------------------------------------
@login_required
def post_create(request):
    """게시글 작성 (로그인 사용자 정보 자동 추가 + 첨부파일 다중 업로드)"""
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
        else:
            messages.error(request, "입력값을 다시 확인해주세요.")
    else:
        form = PostForm()

    return render(request, "board/post_create.html", {"form": form})


# -----------------------------------------------------------------------------
# 📝 게시글 수정
# -----------------------------------------------------------------------------
@login_required
def post_edit(request, pk):
    """게시글 수정 (본인 또는 슈퍼유저만 가능)"""
    post = get_object_or_404(Post, pk=pk)
    is_superuser = (request.user.grade == "superuser")

    # ✅ 수정 권한 검증
    if request.user.id != post.user_id and not is_superuser:
        messages.error(request, "수정 권한이 없습니다.")
        return redirect("post_detail", pk=post.pk)

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)

        # ✅ 첨부파일 삭제 처리
        delete_files = request.POST.getlist("delete_files")
        if delete_files:
            Attachment.objects.filter(id__in=delete_files, post=post).delete()

        # ✅ 수정 및 새 첨부파일 추가
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.user_id = request.user.id
            updated_post.user_name = getattr(request.user, "name", "")
            updated_post.user_branch = getattr(request.user, "branch", "")
            updated_post.save()

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

    attachments = post.attachments.all()

    return render(request, "board/post_edit.html", {
        "form": form,
        "post": post,
        "attachments": attachments,
    })

# ✅ 업무요청서 (제작중)
def support_form(request):
    return render(request, 'board/support_form.html')

# ✅ 업무매뉴얼 (제작중)
def support_manual(request):
    return render(request, 'board/support_manual.html')

# ✅ 영업기준안 (제작중)
def support_rules(request):
    return render(request, 'board/support_rules.html')


# ✅ 업무요청서 페이지
@login_required
def support_form(request):
    """
    파트너 업무요청서 페이지 렌더링
    """
    return render(request, 'board/support_form.html')


# ✅ 대상자 검색 (superuser는 전체, 일반 사용자는 자신의 branch만)
@login_required
def search_user(request):
    keyword = request.GET.get("q", "").strip()
    user = request.user

    if not keyword:
        return JsonResponse({"results": []})

    qs = CustomUser.objects.all()
    if user.grade != "superuser":
        qs = qs.filter(branch=user.branch)

    # ✅ 실제 존재하는 필드 사용
    users = qs.filter(
        Q(name__icontains=keyword) | Q(regist__icontains=keyword)
    ).values(
        "id", "name", "regist", "branch", "enter", "quit"
    )[:20]

    return JsonResponse({"results": list(users)})

@login_required
def generate_request_pdf(request):
    """폼 입력 데이터를 기반으로 워드 템플릿을 채워 PDF로 변환 (Render 환경 호환)"""
    if request.method == "POST":
        # ✅ 1. 폼 데이터 수집
        context = {
            "요청일자": date.today().strftime("%Y-%m-%d"),
            "제목": request.POST.get("title", ""),
            "내용": request.POST.get("content", ""),
        }

        for i in range(1, 6):
            context[f"대상{i}(성명)"] = request.POST.get(f"target_name_{i}", "")
            context[f"대상{i}(사번)"] = request.POST.get(f"target_code_{i}", "")
            context[f"대상{i}(입사)"] = request.POST.get(f"target_join_{i}", "")
            context[f"대상{i}(퇴사)"] = request.POST.get(f"target_leave_{i}", "")
            context[f"계약{i}(보험사)"] = request.POST.get(f"insurer_{i}", "")
            context[f"계약{i}(증권번호)"] = request.POST.get(f"policy_no_{i}", "")
            context[f"계약{i}(계약자)"] = request.POST.get(f"contractor_{i}", "")
            context[f"계약{i}(보험료)"] = request.POST.get(f"premium_{i}", "")

        # ✅ 2. Render 환경에서도 접근 가능한 절대경로 설정
        template_path = os.path.join(settings.BASE_DIR, "media", "파트너 업무요청서.docx")
        if not os.path.exists(template_path):
            return JsonResponse({"error": f"템플릿 파일을 찾을 수 없습니다: {template_path}"}, status=404)

        doc = Document(template_path)

        # ✅ 3. 텍스트 치환
        for p in doc.paragraphs:
            for key, val in context.items():
                placeholder = f"{{{{ {key} }}}}"
                if placeholder in p.text:
                    p.text = p.text.replace(placeholder, str(val))

        # ✅ 4. 임시 저장 (Render에서 /tmp 경로만 쓰기 가능)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_doc = os.path.join(tmpdir, "temp.docx")
            tmp_pdf = os.path.join(tmpdir, "output.pdf")
            doc.save(tmp_doc)

            # ✅ 5. docx → pdf 변환 (LibreOffice headless 모드)
            try:
                subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pdf", tmp_doc, "--outdir", tmpdir],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except Exception as e:
                return JsonResponse({"error": f"PDF 변환 중 오류: {str(e)}"}, status=500)

            # ✅ 6. PDF 읽어서 응답 반환
            with open(tmp_pdf, "rb") as f:
                pdf_bytes = f.read()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="업무요청서.pdf"'
            return response