# ===========================================
# 📂 board/utils/pdf_support_utils.py
# ===========================================
# 업무요청서 PDF 생성 유틸 — ReportLab 기반 (FINAL)
#
# ✅ Policy
# - board 사용 가능: superuser / head / leader
# - task 전용 실행 시: superuser만 (task_only=True)
#
# ✅ Features
# - 한글폰트 등록 1회
# - 로고/제목/요청자/대상자/계약사항/요청내용/확인란 출력
# - 최상위관리자(head > main_admin > leader > superuser) 우선순위로 찾기
# - branch 표기차(strip/iexact + icontains fallback) 대응
# ===========================================

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.conf import settings
from django.http import HttpResponse
from django.db.models import Case, When, IntegerField

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from accounts.models import CustomUser

logger = logging.getLogger("board.access")

# =========================================================
# Policy / Permission
# =========================================================
BOARD_ALLOWED_GRADES = {"superuser", "head", "leader"}


def _is_allowed_board_user(user: CustomUser, *, task_only: bool = False) -> bool:
    """
    board 접근 정책:
    - 기본: superuser/head/leader
    - task_only=True: superuser만 허용
    """
    grade = getattr(user, "grade", "") or ""
    if task_only:
        return grade == "superuser"
    return grade in BOARD_ALLOWED_GRADES


# =========================================================
# PDF Config
# =========================================================
@dataclass(frozen=True)
class PdfConfig:
    font_name: str = "NotoSansKR"
    font_path: str = os.path.join(settings.BASE_DIR, "static", "fonts", "NotoSansKR-Regular.ttf")
    logo_path: str = os.path.join(settings.BASE_DIR, "static", "images", "logo_korean.png")
    right_margin: int = 40
    left_margin: int = 40
    top_margin: int = 40
    bottom_margin: int = 40

    @property
    def margins(self):
        return dict(
            rightMargin=self.right_margin,
            leftMargin=self.left_margin,
            topMargin=self.top_margin,
            bottomMargin=self.bottom_margin,
        )


PDF = PdfConfig()

# =========================================================
# Font / Styles
# =========================================================
def _ensure_korean_font() -> None:
    """폰트 1회 등록(중복 등록 방지)"""
    if PDF.font_name in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(PDF.font_name, PDF.font_path))


def _build_styles():
    styles = getSampleStyleSheet()

    if "Korean" not in styles:
        styles.add(ParagraphStyle(
            name="Korean",
            fontName=PDF.font_name,
            fontSize=11,
            leading=16,
        ))
    if "TitleBold" not in styles:
        styles.add(ParagraphStyle(
            name="TitleBold",
            fontName=PDF.font_name,
            fontSize=18,
            alignment=1,  # center
            spaceAfter=10,
        ))
    if "RightAlign" not in styles:
        styles.add(ParagraphStyle(
            name="RightAlign",
            fontName=PDF.font_name,
            fontSize=11,
            alignment=2,  # right
        ))
    return styles


# =========================================================
# Table Style
# =========================================================
def base_table_style(font_name: str = PDF.font_name) -> TableStyle:
    return TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])


# =========================================================
# Data Helpers
# =========================================================
def _safe_str(v) -> str:
    return (str(v) if v is not None else "").strip()


def _fmt_user_enter(u: CustomUser) -> str:
    enter = getattr(u, "enter", "") or ""
    if hasattr(enter, "strftime"):
        return enter.strftime("%Y-%m-%d")
    return _safe_str(enter) or "-"


def _is_meaningful_row(values: list[str]) -> bool:
    """
    "-", "", None 같은 값만 있는 행은 제외하기 위한 체크.
    """
    for v in values:
        s = (v or "").strip()
        if s and s != "-":
            return True
    return False


def _fmt_money_from_post(raw: str) -> str:
    s = (raw or "").replace(",", "").strip()
    if not s:
        return "-"
    return f"{int(s):,}" if s.isdigit() else s


# =========================================================
# ✅ Head / Admin Resolver (FIX)
# =========================================================
GRADE_PRIORITY = ["head", "main_admin", "leader", "superuser"]


def _grade_order_case():
    """
    head(0) > main_admin(1) > leader(2) > superuser(3) > others(9)
    """
    whens = [When(grade=g, then=i) for i, g in enumerate(GRADE_PRIORITY)]
    return Case(*whens, default=9, output_field=IntegerField())


def find_branch_head_user(branch: str) -> Optional[CustomUser]:
    """
    지점(branch) 기준 최상위관리자(head/main_admin/leader/superuser)를 찾아 반환.
    - branch 표기차/공백 대비: strip + iexact 우선, 없으면 icontains fallback
    - grade 우선순위 적용
    """
    b = (branch or "").strip()
    if not b:
        return None

    qs = (
        CustomUser.objects
        .filter(branch__iexact=b, grade__in=GRADE_PRIORITY)
        .annotate(_grade_order=_grade_order_case())
        .order_by("_grade_order", "id")
    )
    u = qs.first()
    if u:
        return u

    qs2 = (
        CustomUser.objects
        .filter(branch__icontains=b, grade__in=GRADE_PRIORITY)
        .annotate(_grade_order=_grade_order_case())
        .order_by("_grade_order", "id")
    )
    return qs2.first()


def find_part_officer(part: str) -> Optional[CustomUser]:
    """
    사업부장(기존 로직 유지):
    - part 기준 grade=superuser 첫번째
    """
    p = (part or "").strip()
    if not p:
        return None
    return CustomUser.objects.filter(part=p, grade="superuser").first()


# =========================================================
# Main: PDF Generator
# =========================================================
def generate_request_support(request, *, task_only: bool = False):
    """
    [유틸함수] 업무요청서 PDF 생성
    - 요청자, 대상자, 계약사항, 요청내용 포함
    - logo + 한글폰트 + 확인란(최상위관리자/사업부장)
    - 정책 방어(task_only 옵션 제공)
    """
    if request.method != "POST":
        return None  # 뷰 단에서 redirect 처리

    user = getattr(request, "user", None)
    if not user or not _is_allowed_board_user(user, task_only=task_only):
        logger.warning("[PDF] Support blocked by policy: user=%s", getattr(user, "id", None))
        return None

    try:
        _ensure_korean_font()
        styles = _build_styles()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="업무요청서.pdf"'
        doc = SimpleDocTemplate(response, pagesize=A4, **PDF.margins)

        elements = []

        # -------------------------------------------
        # 🏢 로고 + 제목
        # -------------------------------------------
        if os.path.exists(PDF.logo_path):
            elements.append(Image(PDF.logo_path, width=140, height=20, hAlign="LEFT"))

        elements += [
            Paragraph("<b>파트너 업무요청서</b>", styles["TitleBold"]),
            Paragraph(f"요청일자 : {date.today():%Y-%m-%d}", styles["RightAlign"]),
            Spacer(1, 15),
        ]

        # -------------------------------------------
        # 👤 요청자 정보
        # -------------------------------------------
        requester_branch = _safe_str(getattr(user, "branch", ""))
        requester_part = _safe_str(getattr(user, "part", ""))

        requester_data = [
            ["성명", "사번", "소속", "입사일"],
            [
                _safe_str(getattr(user, "name", "")) or "-",
                _safe_str(getattr(user, "id", "")) or "-",
                requester_branch or "-",
                _fmt_user_enter(user),
            ],
        ]
        t1 = Table(requester_data, colWidths=[120, 100, 140, 140])
        t1.setStyle(base_table_style())
        elements += [Paragraph("요청자", styles["Korean"]), t1, Spacer(1, 20)]

        # -------------------------------------------
        # 🎯 대상자 정보 (최대 5명)
        # -------------------------------------------
        target_rows = [["성명", "사번", "입사일", "퇴사일"]]
        for i in range(1, 6):
            row = [
                _safe_str(request.POST.get(f"target_name_{i}", "-")) or "-",
                _safe_str(request.POST.get(f"target_code_{i}", "-")) or "-",
                _safe_str(request.POST.get(f"target_join_{i}", "-")) or "-",
                _safe_str(request.POST.get(f"target_leave_{i}", "-")) or "-",
            ]
            if _is_meaningful_row(row):
                target_rows.append(row)

        if len(target_rows) == 1:
            target_rows.append(["-", "-", "-", "-"])

        t2 = Table(target_rows, colWidths=[120, 100, 140, 140])
        t2.setStyle(base_table_style())
        elements += [Paragraph("대상자", styles["Korean"]), t2, Spacer(1, 20)]

        # -------------------------------------------
        # 💼 계약사항 (최대 5건)
        # -------------------------------------------
        contract_rows = [["보험사", "증권번호", "계약자(피보험자)", "보험료"]]
        for i in range(1, 6):
            row = [
                _safe_str(request.POST.get(f"insurer_{i}", "-")) or "-",
                _safe_str(request.POST.get(f"policy_no_{i}", "-")) or "-",
                _safe_str(request.POST.get(f"contractor_{i}", "-")) or "-",
                _fmt_money_from_post(request.POST.get(f"premium_{i}", "")),
            ]
            if _is_meaningful_row(row):
                contract_rows.append(row)

        if len(contract_rows) == 1:
            contract_rows.append(["-", "-", "-", "-"])

        t3 = Table(contract_rows, colWidths=[120, 140, 140, 100])
        t3.setStyle(base_table_style())
        elements += [Paragraph("계약사항", styles["Korean"]), t3, Spacer(1, 20)]

        # -------------------------------------------
        # 📝 요청 내용
        # -------------------------------------------
        title = _safe_str(request.POST.get("title", "")) or "-"
        content = _safe_str(request.POST.get("content", "")) or "-"

        content_table = [
            ["제목", Paragraph(title, styles["Korean"])],
            ["내용", Paragraph(content, styles["Korean"])],
        ]
        t4 = Table(content_table, colWidths=[60, 440], minRowHeights=[20, 200])
        t4.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), PDF.font_name),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("BACKGROUND", (0, 0), (0, 1), colors.whitesmoke),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 1), "CENTER"),
        ]))
        elements += [Paragraph("요청내용", styles["Korean"]), t4, Spacer(1, 25)]

        # -------------------------------------------
        # ✅ 최상위관리자 확인 (FIXED)
        # -------------------------------------------
        head_user = find_branch_head_user(requester_branch)
        head_name = _safe_str(getattr(head_user, "name", "")) or "(미등록)"
        confirm_admin = (
            f"최상위관리자 확인 : {requester_branch or '-'} 본부장(사업단장)"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{head_name}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
        )
        elements.append(Paragraph(confirm_admin, styles["RightAlign"]))
        elements.append(Spacer(1, 20))

        # -------------------------------------------
        # ✅ 사업부장 자서 (기존 로직 유지)
        # -------------------------------------------
        officer = find_part_officer(requester_part)
        officer_name = _safe_str(getattr(officer, "name", "")) or "(미등록)"
        confirm_officer = (
            f"사업부장 자서확인 : {requester_part or '-'} 사업부장"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{officer_name}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
        )
        elements.append(Paragraph(confirm_officer, styles["RightAlign"]))
        elements.append(Spacer(1, 20))

        # -------------------------------------------
        # 🔧 PDF 빌드
        # -------------------------------------------
        doc.build(elements)
        logger.info("[PDF] 업무요청서 생성 완료 — %s (%s)", getattr(user, "name", ""), requester_branch)
        return response

    except Exception as e:
        logger.error("[PDF 생성 오류] %s", e, exc_info=True)
        return None
