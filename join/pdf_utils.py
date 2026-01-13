# manual/pdf_utils.py
# -*- coding: utf-8 -*-
import io
import os
import tempfile
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


# ---------------- 보험사명 감지 ----------------
def detect_pdf_type_from_text(page):
    """
    보험사 키워드를 바탕으로 페이지 타입과 오프셋을 반환합니다.
    - 일반 그룹은 int(OFFSET_X)를 반환
    - '농협생명'은 필드별 dict 오프셋을 반환
    """
    text = page.get_text("text")
    all_keywords = [
        "DB생명", "삼성생명", "신한라이프", "한화생명", "카디프생명",
        "메트라이프생명", "교보생명", "KDB생명",
        "IBK연금보험", "푸본현대생명", "KB라이프생명",
        "DGB생명", "흥국생명", "미래에셋", "ABL생명", "농협생명", "Chubb", "처브라이프"
    ]
    detected = [kw for kw in all_keywords if kw in text]

    # ✅ 기본 그룹 분류 (오프셋 조정)
    if len(detected) > 3:
        return ("보험사 목록 페이지", 85)
    if any(k in text for k in ["DB생명", "삼성생명", "신한라이프", "한화생명", "카디프생명", "메트라이프생명", "교보생명", "KDB생명"]):
        return ("그룹190", 190)
    if any(k in text for k in ["IBK연금보험", "푸본현대생명", "KB라이프생명", "DGB생명", "흥국생명"]):
        return ("그룹130", 130)
    if any(k in text for k in ["미래에셋", "ABL생명"]):
        return ("그룹140", 140)

    # ✅ 농협생명 전용 필드별 오프셋 (dict 반환)
    if "농협생명" in text:
        nh_offsets = {
            "성명": 60, "성 명": 60,
            "주민등록번호": 30, "주민번호": 30,
            "휴대전화번호": 60, "휴대폰번호": 60, "H.P": 60, "핸드폰번호": 60
        }
        return ("농협생명", nh_offsets)

    if "Chubb" in text or "처브라이프" in text:
        return ("Chubb", 50)

    return ("기타", 50)


# ---------------- 설명문 감지 ----------------
def is_explaining_sentence(sentence):
    explain_triggers = ["①", "②", "③", "개인식별정보", "고유식별정보"]
    return any(t in sentence for t in explain_triggers)


# ---------------- 쉼표 기반 인적문장 감지 ----------------
def is_sensitive_sentence(sentence):
    info_words = [
        "성명", "이름", "생년월일", "성별", "주소", "우편번호", "전화번호",
        "휴대전화번호", "휴대폰번호", "E-mail", "전자우편주소",
        "주민등록번호", "운전면허증번호", "외국인등록번호", "여권번호", "경력", "계좌번호"
    ]
    if "," in sentence:
        return sum(1 for w in info_words if w in sentence) >= 2
    return False


# ---------------- 내부: 페이지별 오버레이 적용 ----------------
def _apply_pdf_overlays(doc, data):
    """
    main(after).py의 고급 규칙을 Django 유틸에 맞게 이식.
    doc: fitz.Document (열려 있는 PDF)
    data: {'name','ssn','phone','address', ...}
    """
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))

    name_keywords = ["성명", "성 명", "이름", "이 름", "설계사 성명", "신청인", "신 청 인", "성명 :"]
    ssn_keywords = ["주민번호", "주민 등록 번호", "주민등록번호", "주 민 등 록 번 호"]
    phone_keywords = ["휴대전화번호", "휴대번호", "H.P", "핸드폰번호", "휴대폰번호"]
    birth_keywords = ["생년월일", "출생일", "생 년 월 일"]
    addr_keywords = ["주소", "주 소"]

    OFFSET_Y = -3
    FONT_SIZE = 12
    ADDR_FONT = 9

    def clamp_x(x, page_width, margin=50):
        return min(max(x, margin), page_width - margin)

    # 처브라이프 기준 페이지 상태 (함수 호출마다 초기화)
    chubb_start_page = None

    total_pages = len(doc)
    for page_index, page in enumerate(doc):
        text_page = page.get_text("text")
        page_height = page.rect.height
        page_width = page.rect.width

        # 보험사 감지 (dict/int 모두 대응)
        result = detect_pdf_type_from_text(page)
        doc_type = result[0]
        if isinstance(result[1], dict):
            field_offsets = result[1]  # 농협생명
            OFFSET_X = 0
        else:
            field_offsets = {}
            OFFSET_X = result[1]

        # 신고신청서 여부
        is_report = ("신고신청서" in text_page) or ("신고 신청서" in text_page)

        # 주소 입력 금지 그룹
        address_blocked_groups = ["그룹190", "그룹130", "그룹140", "농협생명"]
        block_address_input = doc_type in address_blocked_groups
        if block_address_input:
            print(f"[BLOCK-ADDR] {doc_type} 페이지 → 주소 입력 금지")

        # PDF 쓰기 준비
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))
        c.setFont("HYSMyeongJo-Medium", FONT_SIZE)

        # --------- 별지서식 제8호 전용 처리 ---------
        if "별지서식 제8호" in text_page:
            print("[CUSTOM-SKIP] 별지서식 제8호 감지 → 기본 name_keywords 입력 생략")
            rects = page.search_for("신 청 인")
            if rects:
                rect = rects[0]
                x = rect.x1 + 30
                y = page_height - rect.y1 - 5
                c.drawString(x, y, data.get("name", ""))
                print(f"[CUSTOM-DRAW] '신 청 인 :' → ({x:.1f},{y:.1f}) {data.get('name','')}")
            c.save()
            packet.seek(0)
            overlay_pdf = fitz.open("pdf", packet.read())
            page.show_pdf_page(page.rect, overlay_pdf, 0)
            continue

        # --------- 일반 입력 함수 ---------
        def draw_right(keyword_list, value, move_x=0, move_y=0, font_size=None):
            if not value:
                return False
            for keyword in keyword_list:
                rects = page.search_for(keyword)
                for rect in rects:
                    # 상단 15% 영역은 스킵
                    if rect.y0 < page_height * 0.15:
                        continue

                    # 주변 문맥 검사로 설명/민감 문장 제외
                    nearby_rect = fitz.Rect(rect.x0 - 250, rect.y0 - 40, rect.x1 + 250, rect.y1 + 40)
                    nearby_text = page.get_text("text", clip=nearby_rect) or ""
                    for line in nearby_text.splitlines():
                        if is_explaining_sentence(line) or is_sensitive_sentence(line):
                            return False

                    # 기본 X좌표
                    x = rect.x1 + OFFSET_X + move_x

                    # 농협생명 전용: 필드별 X 보정
                    if doc_type == "농협생명" and field_offsets:
                        for k, adj in field_offsets.items():
                            if k in keyword:
                                x += adj
                                print(f"[NH-OFFSET] '{keyword}' → +{adj}px 적용")
                                break

                    x = clamp_x(x, page_width)
                    y = page_height - rect.y1 + OFFSET_Y + move_y

                    # 폰트 크기 임시 변경
                    if font_size:
                        c.setFont("HYSMyeongJo-Medium", font_size)
                    c.drawString(x, y, value)
                    if font_size:
                        c.setFont("HYSMyeongJo-Medium", FONT_SIZE)

                    print(f"[DEBUG] '{keyword}' → ({x:.1f},{y:.1f}) {value}")
                    return True
            return False

        # --------- 기본 입력 (특정 기준문자 전 페이지) ---------
        if "2007121497" not in text_page:
            # 이름은 소제목 배치에 따라 세밀 보정
            name_adjustments = {
                "성명": {"move_x": -5, "move_y": 0},
                "성 명": {"move_x": 30, "move_y": +5},
            }
            for keyword, adj in name_adjustments.items():
                if keyword in text_page:
                    draw_right([keyword], data.get("name", ""), adj["move_x"], adj["move_y"])
                    break
            else:
                draw_right(name_keywords, data.get("name", ""), move_x=-10)

            draw_right(ssn_keywords, data.get("ssn", ""))
            draw_right(birth_keywords, data.get("ssn", "")[:6])
            draw_right(phone_keywords, data.get("phone", ""), move_x=-10)

            # 주소는 신고신청서가 아니고, 금지 그룹이 아닐 때만
            if (not is_report) and (not block_address_input):
                draw_right(addr_keywords, data.get("address", ""), move_x=-30, font_size=ADDR_FONT)

        # --------- 2007121497 이후 강제입력 ---------
        agency_rects = page.search_for("2007121497")
        if agency_rects:
            agency_y = agency_rects[0].y0
            for kw, val, offset, fsize in [
                (birth_keywords, data.get("ssn", "")[:6], 90, FONT_SIZE),
                (phone_keywords, data.get("phone", ""), 80, FONT_SIZE),
                (["성명", "성 명"], data.get("name", ""), 130, FONT_SIZE),
                (addr_keywords, data.get("address", ""), 50, ADDR_FONT),
            ]:
                rects = []
                for k in kw:
                    rects += list(page.search_for(k))
                rects = [r for r in rects if r.y0 > agency_y - 2]
                if rects:
                    r = sorted(rects, key=lambda rr: rr.y0)[0]
                    x = clamp_x(r.x1 + offset, page_width)
                    y_adjust = 5 if kw == addr_keywords else 0
                    y = page_height - r.y1 + OFFSET_Y + y_adjust
                    c.setFont("HYSMyeongJo-Medium", fsize)
                    c.drawString(x, y, val)
                    c.setFont("HYSMyeongJo-Medium", FONT_SIZE)

        # --------- 위촉신청서 강제입력 (특정사명) ---------
        if any(k in text_page for k in ["KDB생명 위촉신청서", "KB라이프생명 위촉신청서", "카디프생명 위촉신청서", "IBK연금보험 위촉신청서"]):
            rects = []
            for kw in ["성명", "성 명"]:
                rects += list(page.search_for(kw))
            if rects:
                r = sorted(rects, key=lambda rr: rr.y0)[0]
                x = clamp_x(r.x1 + 150, page_width)
                y = page_height - r.y1 + OFFSET_Y
                c.drawString(x, y, data.get("name", ""))

        # --------- 신고신청서 처리 ---------
        if is_report:
            addr_rects = page.search_for("우편번호")
            if addr_rects:
                rect = addr_rects[0]
                x = clamp_x(rect.x1 + 45, page_width)
                y = page_height - rect.y1 + OFFSET_Y + 1
                c.setFont("HYSMyeongJo-Medium", ADDR_FONT)
                c.drawString(x, y, data.get("address", ""))
                c.setFont("HYSMyeongJo-Medium", FONT_SIZE)

            applicant_rects = page.search_for("신청인")
            if applicant_rects:
                rect = applicant_rects[0]
                x = rect.x1 + 80
                y = page_height - rect.y1 - 4
                c.saveState()
                c.translate(-70, 0)
                c.drawString(x, y, data.get("name", ""))
                c.restoreState()

        # --------- 2/2 페이지 처리 ---------
        if "2/2" in text_page:
            rects = []
            for kw in ["신 청 인", "신청 인", "신청인"]:
                rects += list(page.search_for(kw))
            if rects:
                rect = sorted(rects, key=lambda r: r.y1, reverse=True)[0]
                x = rect.x1 + 30
                y = page_height - rect.y1 + 5
                c.drawString(x, y, data.get("name", ""))

        # --------- 처브라이프 특수 처리 ---------
        if "처브라이프" in text_page and "GA사업부 Agent 위촉계약서" in text_page:
            hp_rects = page.search_for("H.P")
            if hp_rects:
                hp_rect = hp_rects[0]
                x = hp_rect.x0 + 65
                y = page_height - hp_rect.y0 + 8
                c.drawString(x, y, data.get("name", ""))
                print(f"[FORCE-FIX] H.P 위 성명 입력 → ({x:.1f}, {y:.1f}) {data.get('name','')}")

        # 기준 페이지 위치 저장
        if "처브라이프" in text_page and "GA사업부 Agent 위촉계약서" in text_page:
            chubb_start_page = page_index
            print(f"[DETECT] 처브라이프 위촉계약서 시작 → 기준 페이지 {page_index+1}")

        # 기준으로부터 4p 뒤 하단 '성명 :' 강제 입력
        if (chubb_start_page is not None) and (page_index == chubb_start_page + 4):
            print(f"[FORCE] 처브라이프 기준 4페이지 뒤({page_index+1}p) 하단 '성명 :' 강제 입력")
            name_rects = page.search_for("성명")
            if name_rects:
                rect = sorted(name_rects, key=lambda r: r.y0, reverse=True)[0]
                x = rect.x1 + 20
                y = page_height - rect.y0 - 15
                c.setFont("HYSMyeongJo-Medium", FONT_SIZE)
                c.drawString(x, y, data.get("name", ""))
                print(f"[FORCE-CHUBB] 하단 표 성명 입력 완료 → ({x:.1f},{y:.1f}) {data.get('name','')}")
            else:
                print(f"[WARN] {page_index+1}p '성명' 텍스트 감지 실패 → 스킵")

        # --------- 개인신용정보 동의서 제목 옆 성명 ---------
        if "개인신용정보의 수집¶이용¶제공¶조회 동의서" in text_page:
            title_rects = page.search_for("개인신용정보의 수집¶이용¶제공¶조회 동의서")
            if title_rects:
                rect = title_rects[0]
                x = rect.x1 + 90
                y = page_height - rect.y1 + 20
                c.setFont("HYSMyeongJo-Medium", FONT_SIZE)
                c.drawString(x, y, data.get("name", ""))
                print(f"[FORCE-INFO] 동의서 제목 옆 ({x:.1f},{y:.1f}) 성명 입력 → {data.get('name','')}")

        # --------- 완전판매 준수 서약서: '앞 장' 하단 성명 ---------
        if "완전판매 준수 서약서" in text_page and page_index > 0:
            print(f"[FORCE] 완전판매 준수 서약서 감지({page_index+1}p) → 앞장({page_index}p) 하단 성명 입력")
            prev_page = doc.load_page(page_index - 1)
            prev_height = prev_page.rect.height
            name_rects_prev = prev_page.search_for("성명")
            if name_rects_prev:
                bottom_rects = [r for r in name_rects_prev if r.y0 > prev_height * 0.7]
                if bottom_rects:
                    rect = sorted(bottom_rects, key=lambda r: r.y0, reverse=True)[0]
                    x = rect.x1 + 15
                    y = prev_height - rect.y0 - 10

                    packet_prev = io.BytesIO()
                    c_prev = canvas.Canvas(packet_prev, pagesize=(prev_page.rect.width, prev_height))
                    c_prev.setFont("HYSMyeongJo-Medium", FONT_SIZE)
                    c_prev.drawString(x, y, data.get("name", ""))
                    c_prev.save()
                    packet_prev.seek(0)

                    overlay_prev = fitz.open("pdf", packet_prev.read())
                    prev_page.show_pdf_page(prev_page.rect, overlay_prev, 0)
                    print(f"[FORCE-WPS-PREV] 앞장 하단 성명 입력 완료 → ({x:.1f}, {y:.1f}) {data.get('name','')}")
                else:
                    print("[WARN] 앞장 하단에서 '성명' 텍스트를 찾지 못했습니다.")
            else:
                print("[WARN] 앞장에 '성명' 텍스트 감지 실패 → 입력 스킵")

        # --------- 페이지 오버레이 병합 ---------
        c.save()
        packet.seek(0)
        overlay_pdf = fitz.open("pdf", packet.read())
        page.show_pdf_page(page.rect, overlay_pdf, 0)


# ---------------- 공개 API: 템플릿 입력 후 파일 저장 ----------------
def fill_pdf(pdf_template_path, data) -> str:
    """
    템플릿 PDF 경로와 데이터(dict)를 받아,
    자동입력된 PDF 임시파일 경로를 반환합니다.
    - data 예시: {
        "name": "...", "ssn": "...", "phone": "...",
        "address": "...", "email": "...", "postcode": "...", "address_detail": "..."
      }
    """
    # 임시 파일 경로 생성
    fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    # PDF 열기
    doc = fitz.open(pdf_template_path)

    # 오버레이 적용
    _apply_pdf_overlays(doc, data)

    # 압축 저장(용량 절감)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return output_path
