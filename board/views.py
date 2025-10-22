# django_ma/board/views.py

# ===============================
# ✅ 표준 라이브러리
# ===============================
import os
import logging
from datetime import date, datetime

# ===============================
# ✅ Django 기본 모듈
# ===============================
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

# ===============================
# ✅ ReportLab (PDF 생성용)
# ===============================
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# ===============================
# ✅ 로컬 앱 모듈
# ===============================
from accounts.models import CustomUser
from .forms import PostForm, CommentForm
from .models import Post, Attachment, Comment

# ✅ 전역에서 한 번만 로드
logger = logging.getLogger(__name__)
User = get_user_model()

# -------------------------------------------------------------------
# 📋 공용 상수
# -------------------------------------------------------------------
STATUS_CHOICES = ['확인중', '진행중', '보완요청', '완료', '반려']

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

# ✅ 업무매뉴얼 (제작중)
def support_manual(request):
    return render(request, 'board/support_manual.html')

# ✅ 영업기준안 (제작중)
def support_rules(request):
    return render(request, 'board/support_rules.html')

# ✅ 업무요청서 페이지
@login_required
def support_form(request):
    """파트너 업무요청서 페이지"""
    return render(request, 'board/support_form.html')


# -------------------------------------------------------------------
# 🧾 PDF 유틸리티
# -------------------------------------------------------------------
def register_korean_font():
    """NotoSansKR 폰트를 안전하게 등록"""
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "NotoSansKR-Regular.ttf")
    if not pdfmetrics.getRegisteredFontNames() or "NotoSansKR" not in pdfmetrics.getRegisteredFontNames():
        try:
            pdfmetrics.registerFont(TTFont("NotoSansKR", font_path))
        except Exception as e:
            logger.warning(f"[PDF] 폰트 등록 실패: {e}")


def build_pdf_response(filename="output.pdf"):
    """PDF 응답 객체 생성"""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def create_pdf_document(response, elements):
    """ReportLab PDF 문서 생성"""
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    try:
        doc.build(elements)
    except Exception as e:
        logger.error(f"[PDF 생성 오류] {e}")
        raise


# -------------------------------------------------------------------
# 🔍 대상자 검색 (superuser는 전체, 일반 사용자는 자신의 branch만)
# -------------------------------------------------------------------
@login_required
def search_user(request):
    keyword = request.GET.get("q", "").strip()
    user = request.user
    if not keyword:
        return JsonResponse({"results": []})

    qs = CustomUser.objects.all()
    if user.grade != "superuser":
        qs = qs.filter(branch=user.branch)

    users = qs.filter(
        Q(name__icontains=keyword) | Q(regist__icontains=keyword)
    ).values("id", "name", "regist", "branch", "enter", "quit")[:20]

    return JsonResponse({"results": list(users)})


# -------------------------------------------------------------------
# 🧾 업무요청서 PDF 생성 (xhtml2pdf)
# -------------------------------------------------------------------
@login_required
def generate_request_pdf(request):
    """폼 입력값을 기반으로 업무요청서 PDF 생성"""
    if request.method != "POST":
        return redirect("support_form")

    # ==========================================
    # ✅ 폰트 및 기본 설정
    # ==========================================
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "NotoSansKR-Regular.ttf")
    pdfmetrics.registerFont(TTFont("NotoSansKR", font_path))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="업무요청서.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    # ==========================================
    # ✅ 스타일 정의
    # ==========================================
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Korean", fontName="NotoSansKR", fontSize=11, leading=16))
    styles.add(ParagraphStyle(name="TitleBold", fontName="NotoSansKR", fontSize=18, leading=22,
                              alignment=1, spaceAfter=10))
    styles.add(ParagraphStyle(name="RightAlign", fontName="NotoSansKR", fontSize=11, alignment=2))
    styles.add(ParagraphStyle(name="RightAdmin", fontName="NotoSansKR", fontSize=11, alignment=2))

    elements = []

    # ==========================================
    # ✅ 제목 / 요청일자
    # ==========================================
    elements.append(Paragraph("<b>파트너 업무요청서</b>", styles["TitleBold"]))
    elements.append(Spacer(1, 4))

    elements.append(Paragraph(f"요청일자 : {date.today().strftime('%Y-%m-%d')}", styles["RightAlign"]))
    elements.append(Spacer(1, 15))

    # ==========================================
    # ✅ 요청자 정보
    # ==========================================
    enter_value = getattr(request.user, "enter", None)
    if enter_value:
        try:
            enter_value = enter_value.strftime("%Y-%m-%d")
        except Exception:
            enter_value = str(enter_value)
    else:
        enter_value = "-"

    requester_table = [
        ["성명", "사번", "소속", "입사일"],
        [
            request.user.name,
            str(request.user.id),
            request.user.branch,
            enter_value,
        ],
    ]

    elements.append(Paragraph("요청자", styles["Korean"]))
    table1 = Table(requester_table, colWidths=[120, 100, 140, 140])
    table1.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoSansKR"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(table1)
    elements.append(Spacer(1, 20))

    # ==========================================
    # ✅ 대상자 정보
    # ==========================================
    target_rows = [["성명", "사번", "입사일", "퇴사일"]]
    for i in range(1, 6):
        name = request.POST.get(f"target_name_{i}", "").strip()
        code = request.POST.get(f"target_code_{i}", "").strip()
        join = request.POST.get(f"target_join_{i}", "").strip()
        leave = request.POST.get(f"target_leave_{i}", "").strip()
        if any([name, code, join, leave]):
            target_rows.append([name or "-", code or "-", join or "-", leave or "-"])

    if len(target_rows) == 1:
        target_rows.append(["-", "-", "-", "-"])

    elements.append(Paragraph("대상자", styles["Korean"]))
    table2 = Table(target_rows, colWidths=[120, 100, 140, 140])
    table2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoSansKR"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(table2)
    elements.append(Spacer(1, 20))

    # ==========================================
    # ✅ 계약 내용
    # ==========================================
    elements.append(Paragraph("계약사항", styles["Korean"]))
    contract_rows = [["보험사", "증권번호", "계약자(피보험자)", "보험료"]]

    for i in range(1, 6):
        insurer = request.POST.get(f"insurer_{i}", "").strip()
        policy_no = request.POST.get(f"policy_no_{i}", "").strip()
        contractor = request.POST.get(f"contractor_{i}", "").strip()
        premium_raw = request.POST.get(f"premium_{i}", "").replace(",", "").strip()

        # ✅ 숫자만 추출 후 천단위 구분 적용
        premium = ""
        if premium_raw.isdigit():
            premium = f"{int(premium_raw):,}"
        elif premium_raw:
            premium = premium_raw  # 혹시 문자 포함 시 그대로 표시

        if any([insurer, policy_no, contractor, premium]):
            contract_rows.append([insurer or "-", policy_no or "-", contractor or "-", premium or "-"])

    if len(contract_rows) == 1:
        contract_rows.append(["-", "-", "-", "-"])

    table3 = Table(contract_rows, colWidths=[120, 140, 140, 100])
    table3.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoSansKR"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),   # 머릿말 행(첫 번째 행)은 전체 가운데 정렬
        ("ALIGN", (0, 1), (2, -1), "CENTER"),   # 보험료 제외한 나머지 데이터 열은 가운데 정렬
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),    # 보험료 열만 오른쪽 정렬
    ]))
    elements.append(table3)
    elements.append(Spacer(1, 20))

    # ==========================================
    # ✅ 요청 내용
    # ==========================================
    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()

    title_paragraph = Paragraph(title or "-", styles["Korean"])
    content_paragraph = Paragraph(content or "-", styles["Korean"])

    elements.append(Paragraph("요청내용", styles["Korean"]))

    content_table = [
        ["제목", title_paragraph],
        ["내용", content_paragraph],
    ]

    table4 = Table(content_table, colWidths=[60, 440], minRowHeights=[20, 200])
    table4.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "NotoSansKR"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 14),
        ("ROWHEIGHTS", (1, 1), (1, 1)),
    ]))
    elements.append(table4)
    elements.append(Spacer(1, 25))

    # ==========================================
    # ✅ 본부장(사업단장) 표시
    # ==========================================
    main_admin = CustomUser.objects.filter(branch=request.user.branch, grade="main_admin").first()
    admin_name = main_admin.name if main_admin else ""

    confirm_text = (
        f'최상위관리자 확인 : {request.user.branch} 본부장(사업단장)'
        f'<b>&nbsp;&nbsp;{admin_name}&nbsp;&nbsp;</b>(서명)'
    )
    elements.append(Paragraph(confirm_text, styles["RightAdmin"]))

    # ==========================================
    # ✅ PDF 빌드
    # ==========================================
    doc.build(elements)
    return response

