# ===========================================
# 📂 board/utils/pdf_utils.py
# ===========================================
# 업무요청서 PDF 생성 유틸 — ReportLab 기반
# ===========================================

import os
import logging
from datetime import date
from django.conf import settings
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from accounts.models import CustomUser

# -------------------------------------------
# ✅ 상수 정의 (PDF 설정)
# -------------------------------------------
PDF_CONFIG = {
    "FONT_NAME": "NotoSansKR",
    "FONT_PATH": os.path.join(settings.BASE_DIR, "static", "fonts", "NotoSansKR-Regular.ttf"),
    "LOGO_PATH": os.path.join(settings.BASE_DIR, "static", "images", "logo_korean.png"),
    "MARGINS": dict(rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40),
}

logger = logging.getLogger("board.access")


# -------------------------------------------
# ✅ Table 공통 스타일
# -------------------------------------------
def base_table_style(font_name=PDF_CONFIG["FONT_NAME"]):
    """기본 테이블 스타일 생성"""
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ])


# -------------------------------------------
# ✅ 업무요청서 PDF 생성 메인 함수
# -------------------------------------------
def generate_request_support(request):
    """
    [유틸함수] 업무요청서 PDF 생성
    - 요청자, 대상자, 계약사항, 요청내용 포함
    - logo + 한글폰트 + 자동 서명 표시
    """
    if request.method != "POST":
        return None  # 뷰 단에서 redirect 처리

    # 🔸 폰트 등록
    if PDF_CONFIG["FONT_NAME"] not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_CONFIG["FONT_NAME"], PDF_CONFIG["FONT_PATH"]))

    # 🔸 기본 설정
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="업무요청서.pdf"'
    doc = SimpleDocTemplate(response, pagesize=A4, **PDF_CONFIG["MARGINS"])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Korean", fontName=PDF_CONFIG["FONT_NAME"], fontSize=11, leading=16))
    styles.add(ParagraphStyle(name="TitleBold", fontName=PDF_CONFIG["FONT_NAME"], fontSize=18, alignment=1, spaceAfter=10))
    styles.add(ParagraphStyle(name="RightAlign", fontName=PDF_CONFIG["FONT_NAME"], fontSize=11, alignment=2))

    elements = []

    # -------------------------------------------
    # 🏢 로고 + 제목
    # -------------------------------------------
    logo_path = PDF_CONFIG["LOGO_PATH"]
    if os.path.exists(logo_path):
        elements += [Image(logo_path, width=140, height=20, hAlign="LEFT")]
    elements += [
        Paragraph("<b>파트너 업무요청서</b>", styles["TitleBold"]),
        Paragraph(f"요청일자 : {date.today():%Y-%m-%d}", styles["RightAlign"]),
        Spacer(1, 15),
    ]

    # -------------------------------------------
    # 👤 요청자 정보
    # -------------------------------------------
    enter = getattr(request.user, "enter", "")
    if hasattr(enter, "strftime"):
        enter = enter.strftime("%Y-%m-%d")

    requester_data = [
        ["성명", "사번", "소속", "입사일"],
        [request.user.name, str(request.user.id), request.user.branch, enter or "-"],
    ]
    table1 = Table(requester_data, colWidths=[120, 100, 140, 140])
    table1.setStyle(base_table_style())
    elements += [Paragraph("요청자", styles["Korean"]), table1, Spacer(1, 20)]

    # -------------------------------------------
    # 🎯 대상자 정보
    # -------------------------------------------
    target_rows = [["성명", "사번", "입사일", "퇴사일"]]
    for i in range(1, 6):
        row = [
            request.POST.get(f"target_name_{i}", "-"),
            request.POST.get(f"target_code_{i}", "-"),
            request.POST.get(f"target_join_{i}", "-"),
            request.POST.get(f"target_leave_{i}", "-"),
        ]
        if any(v.strip("-") for v in row):
            target_rows.append(row)
    if len(target_rows) == 1:
        target_rows.append(["-", "-", "-", "-"])

    table2 = Table(target_rows, colWidths=[120, 100, 140, 140])
    table2.setStyle(base_table_style())
    elements += [Paragraph("대상자", styles["Korean"]), table2, Spacer(1, 20)]

    # -------------------------------------------
    # 💼 계약사항
    # -------------------------------------------
    contract_rows = [["보험사", "증권번호", "계약자(피보험자)", "보험료"]]
    for i in range(1, 6):
        premium = request.POST.get(f"premium_{i}", "").replace(",", "")
        premium_fmt = f"{int(premium):,}" if premium.isdigit() else premium
        row = [
            request.POST.get(f"insurer_{i}", "-"),
            request.POST.get(f"policy_no_{i}", "-"),
            request.POST.get(f"contractor_{i}", "-"),
            premium_fmt or "-",
        ]
        if any(v.strip("-") for v in row):
            contract_rows.append(row)
    if len(contract_rows) == 1:
        contract_rows.append(["-", "-", "-", "-"])

    table3 = Table(contract_rows, colWidths=[120, 140, 140, 100])
    table3.setStyle(base_table_style())
    elements += [Paragraph("계약사항", styles["Korean"]), table3, Spacer(1, 20)]

    # -------------------------------------------
    # 📝 요청 내용
    # -------------------------------------------
    title = request.POST.get("title", "-")
    content = request.POST.get("content", "-")

    content_table = [
        ["제목", Paragraph(title, styles["Korean"])],
        ["내용", Paragraph(content, styles["Korean"])],
    ]
    table4 = Table(content_table, colWidths=[60, 440], minRowHeights=[20, 200])
    table4.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), PDF_CONFIG["FONT_NAME"]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("BACKGROUND", (0, 0), (0, 1), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 1), "CENTER"),   
    ]))
    elements += [Paragraph("요청내용", styles["Korean"]), table4, Spacer(1, 25)]

    '''
    # -------------------------------------------
    # ✍️ 요청자 서명란 추가
    # -------------------------------------------
    requester_sign = f"요청자 : {request.user.branch}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{request.user.name}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
    elements.append(Paragraph(requester_sign, styles["RightAlign"]))
    elements.append(Spacer(1, 10))
    '''

    # -------------------------------------------
    # ✅ 본부장 확인
    # -------------------------------------------
    admin = CustomUser.objects.filter(branch=request.user.branch, grade="main_admin").first()
    admin_name = admin.name if admin else "(미등록)"
    confirm_admin = f"최상위관리자 확인 : {request.user.branch} 본부장(사업단장)&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{admin_name}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
    elements.append(Paragraph(confirm_admin, styles["RightAlign"]))
    elements.append(Spacer(1, 20))

    # -------------------------------------------
    # ✅ 사업부장 자서
    # -------------------------------------------
    officer = CustomUser.objects.filter(part=request.user.part, grade="superuser").first()
    officer_name = officer.name if officer else "(미등록)"
    confirm_officer = (
        f"사업부장 자서확인 : {request.user.part} 사업부장&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"{officer_name}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
    )
    elements.append(Paragraph(confirm_officer, styles["RightAlign"]))
    elements.append(Spacer(1, 20))

    # -------------------------------------------
    # 🔧 PDF 빌드
    # -------------------------------------------
    try:
        doc.build(elements)
        logger.info(f"[PDF] 업무요청서 생성 완료 — {request.user.name} ({request.user.branch})")
    except Exception as e:
        logger.error(f"[PDF 생성 오류] {e}")
        return None

    return response