# join/pdf_utils.py
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import io
import os
import tempfile

# detect_pdf_type_from_text(), is_sensitive_sentence() 그대로 사용

def fill_pdf(pdf_template_path, data) -> str:
    doc = fitz.open(pdf_template_path)
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

    name_keywords = ["성명", "성 명", "이름", "이 름", "설계사 성명", "신청인", "성명 :"]
    ssn_keywords = ["주민번호", "주민 등록 번호", "주민등록번호", "주 민 등 록 번 호"]
    phone_keywords = ["휴대전화번호", "휴대번호", "H.P", "핸드폰번호", "휴대폰번호"]
    birth_keywords = ["생년월일", "출생일", "생 년 월 일"]

    OFFSET_Y = -3
    FONT_SIZE = 12

    # 임시 경로에 파일 저장
    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    for page_index, page in enumerate(doc):
        doc_type, OFFSET_X = detect_pdf_type_from_text(page)
        page_height = page.rect.height
        text_page = page.get_text("text")
        is_report_form = "신고신청서" in text_page or "신고 신청서" in text_page

        blocks = page.get_text("blocks")
        table_blocks = [b for b in blocks if (b[2]-b[0]) < 250 and (b[3]-b[1]) < 40]
        anchor = page.search_for("상기 내용이 변경되는 경우")
        anchor_y = anchor[0].y0 if anchor else page.rect.height - 200

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page.rect.width, page.rect.height))
        c.setFont("HYSMyeongJo-Medium", FONT_SIZE)

        def draw_right(keyword_list, value, move_x=0):
            for keyword in keyword_list:
                rects = page.search_for(keyword)
                for rect in rects:
                    if rect.y0 < page.rect.height * 0.15:
                        continue
                    inside_table = any(
                        bx0 <= rect.x0 <= bx1 and by0 <= rect.y0 <= by1
                        for bx0, by0, bx1, by1, *_ in table_blocks
                    )
                    nearby_rect = fitz.Rect(rect.x0 - 250, rect.y0 - 40, rect.x1 + 250, rect.y1 + 40)
                    nearby_text = page.get_text("text", clip=nearby_rect)
                    if (
                        anchor_y and
                        rect.y0 > anchor_y - 600 and
                        rect.y0 > page.rect.height * 0.65 and
                        any((b[2]-b[0]) < 250 and (b[3]-b[1]) < 40 for b in table_blocks)
                    ):
                        pass
                    elif not inside_table:
                        for line in nearby_text.splitlines():
                            if is_sensitive_sentence(line):
                                return False
                    x = rect.x1 + OFFSET_X + move_x
                    y = page_height - rect.y1 + OFFSET_Y
                    c.drawString(x, y, value)
                    return True
            return False

        draw_right(name_keywords, data["name"])
        draw_right(ssn_keywords, data["ssn"])
        draw_right(birth_keywords, data["ssn"][:6])
        draw_right(phone_keywords, data["phone"])

        if is_report_form:
            addr_rects = page.search_for("우편번호")
            if addr_rects:
                rect = addr_rects[0]
                x = rect.x1 + 45
                y = page_height - rect.y1 + OFFSET_Y + 1
                c.drawString(x, y, data["address"])
            applicant_rects = page.search_for("신청인")
            if applicant_rects:
                rect = applicant_rects[0]
                x = rect.x1 + 80
                y = page_height - rect.y1 - 4
                c.saveState()
                c.translate(-70, 0)
                c.drawString(x, y, data["name"])
                c.restoreState()
        else:
            addr_rects = page.search_for("주       소")
            if addr_rects:
                rect = addr_rects[0]
                x = rect.x1 + OFFSET_X + 10
                y = page_height - rect.y1 + OFFSET_Y
                c.drawString(x, y, data["address"])

        c.save()
        packet.seek(0)
        overlay_pdf = fitz.open("pdf", packet.read())
        page.show_pdf_page(page.rect, overlay_pdf, 0)

    doc.save(output_path)
    doc.close()
    return output_path  # PDF 경로 반환
