# ===========================================
# 📂 board/utils/pdf_states_utils.py
# ===========================================
# FA 소명서 PDF 생성 유틸 (대상자 없음)
#
# ✅ Policy
# - board 사용 가능: superuser / head / leader
# - (task 전용은 아님) -> 필요 시 task_only=True로 superuser만 허용 가능
#
# ✅ Notes
# - request.method != POST 이면 None 반환(뷰에서 처리)
# - ReportLab + 한글 폰트 등록 1회 처리
# ===========================================

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.conf import settings
from django.http import HttpResponse

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from accounts.models import CustomUser
from board.policies import is_inactive


logger = logging.getLogger("board.access")


def _is_allowed_board_user(user: CustomUser, *, task_only: bool = False) -> bool:
    grade = getattr(user, "grade", "") or ""
    if task_only:
        return grade == "superuser"
    # states는 기존 정책대로 "inactive만 차단"
    return not is_inactive(user)


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
    def margins(self) -> dict:
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
    """폰트는 프로세스 생명주기 동안 1회만 등록."""
    if PDF.font_name in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(PDF.font_name, PDF.font_path))


def _build_styles():
    styles = getSampleStyleSheet()

    # 이름 충돌 방지
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
# Table Style / Helpers
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


def _safe_str(v) -> str:
    return (str(v) if v is not None else "").strip()


def _fmt_user_enter(u: CustomUser) -> str:
    enter = getattr(u, "enter", "") or ""
    if hasattr(enter, "strftime"):
        return enter.strftime("%Y-%m-%d")
    return _safe_str(enter) or "-"


def _fmt_money_from_post(raw: str) -> str:
    s = (raw or "").replace(",", "").strip()
    if not s:
        return "-"
    return f"{int(s):,}" if s.isdigit() else s


def _is_meaningful_row(values: list[str]) -> bool:
    """
    '-', '', None만 있는 행은 제외.
    """
    for v in values:
        s = (v or "").strip()
        if s and s != "-":
            return True
    return False


# =========================================================
# Branch Head Resolver (for states)
# - 기존 states 로직(main_admin only) 개선
# - branch 표기 차이/공백 + grade 우선순위 적용
# =========================================================
GRADE_PRIORITY = ["head", "main_admin", "leader", "superuser"]


def find_branch_head_user(branch: str) -> Optional[CustomUser]:
    """
    지점 기준 최상위관리자(head/main_admin/leader/superuser) 탐색.
    - branch strip + iexact 우선, 없으면 icontains fallback
    - grade 우선순위 반영은 support_utils에서처럼 annotate Case로 해도 되지만,
      states는 부담 줄이기 위해 2단 탐색 후 grade 우선순위로 파이썬에서 정렬.
    """
    b = (branch or "").strip()
    if not b:
        return None

    qs = CustomUser.objects.filter(branch__iexact=b, grade__in=GRADE_PRIORITY)
    candidates = list(qs)
    if not candidates:
        qs2 = CustomUser.objects.filter(branch__icontains=b, grade__in=GRADE_PRIORITY)
        candidates = list(qs2)

    if not candidates:
        return None

    order_map = {g: i for i, g in enumerate(GRADE_PRIORITY)}
    candidates.sort(key=lambda u: (order_map.get(getattr(u, "grade", ""), 999), getattr(u, "id", 0)))
    return candidates[0]


# =========================================================
# Main: PDF Generator
# =========================================================
def generate_request_states(request, *, task_only: bool = False):
    """
    [유틸함수] FA 소명서 PDF 생성
    - 대상자 섹션 없음
    - 작성자/계약사항/요청내용(제목/발생경위/개선방안)/확인란 포함
    - 권한 정책 방어(task_only 옵션 제공)
    """
    if request.method != "POST":
        return None

    user = getattr(request, "user", None)
    if not user or not _is_allowed_board_user(user, task_only=task_only):
        logger.warning("[PDF] States blocked by policy: user=%s", getattr(user, "id", None))
        return None

    try:
        _ensure_korean_font()
        styles = _build_styles()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="소명서.pdf"'
        doc = SimpleDocTemplate(response, pagesize=A4, **PDF.margins)

        elements = []

        # -------------------------------------------
        # 🏢 로고 + 제목
        # -------------------------------------------
        if os.path.exists(PDF.logo_path):
            elements.append(Image(PDF.logo_path, width=140, height=20, hAlign="LEFT"))

        elements += [
            Paragraph("<b>FA 소명서</b>", styles["TitleBold"]),
            Paragraph(f"요청일자 : {date.today():%Y-%m-%d}", styles["RightAlign"]),
            Spacer(1, 15),
        ]

        # -------------------------------------------
        # 👤 작성자 정보
        # -------------------------------------------
        requester_branch = _safe_str(getattr(user, "branch", "")) or "-"
        requester_data = [
            ["성명", "사번", "소속", "입사일"],
            [
                _safe_str(getattr(user, "name", "")) or "-",
                _safe_str(getattr(user, "id", "")) or "-",
                requester_branch,
                _fmt_user_enter(user),
            ],
        ]
        t1 = Table(requester_data, colWidths=[120, 100, 140, 140])
        t1.setStyle(base_table_style())
        elements += [Paragraph("작성자", styles["Korean"]), t1, Spacer(1, 20)]

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

        t2 = Table(contract_rows, colWidths=[120, 140, 140, 100])
        t2.setStyle(base_table_style())
        elements += [Paragraph("계약사항", styles["Korean"]), t2, Spacer(1, 20)]

        # -------------------------------------------
        # 📝 요청 내용
        # -------------------------------------------
        title = _safe_str(request.POST.get("title", "")) or "-"
        reason = _safe_str(request.POST.get("reason", "")) or "-"
        solution = _safe_str(request.POST.get("solution", "")) or "-"

        content_table = [
            ["제목", Paragraph(title, styles["Korean"])],
            ["발생경위", Paragraph(reason, styles["Korean"])],
            ["개선방안", Paragraph(solution, styles["Korean"])],
        ]
        t3 = Table(content_table, colWidths=[60, 440], minRowHeights=[20, 150, 150])
        t3.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), PDF.font_name),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
            ("BACKGROUND", (0, 0), (0, 2), colors.whitesmoke),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ]))
        elements += [Paragraph("요청내용", styles["Korean"]), t3, Spacer(1, 25)]

        # -------------------------------------------
        # ✍️ 작성자 서명란
        # -------------------------------------------
        requester_sign = (
            f"작성자 : {requester_branch}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{_safe_str(getattr(user, 'name', '')) or '-'}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
        )
        elements.append(Paragraph(requester_sign, styles["RightAlign"]))
        elements.append(Spacer(1, 10))

        # -------------------------------------------
        # ✅ 최상위관리자 확인 (개선 로직)
        # -------------------------------------------
        head_user = find_branch_head_user(requester_branch)
        head_name = _safe_str(getattr(head_user, "name", "")) or "(미등록)"
        confirm_text = (
            f"최상위관리자 확인 : {requester_branch} 본부장(사업단장)"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{head_name}"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(서명)"
        )
        elements.append(Paragraph(confirm_text, styles["RightAlign"]))
        elements.append(Spacer(1, 20))

        # -------------------------------------------
        # 🔧 PDF 빌드
        # -------------------------------------------
        doc.build(elements)
        logger.info("[PDF] FA 소명서 생성 완료 — %s (%s)", getattr(user, "name", ""), requester_branch)
        return response

    except Exception as e:
        logger.error("[PDF 생성 오류] %s", e, exc_info=True)
        return None
