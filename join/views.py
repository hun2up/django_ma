# join/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import JoinInfo
from django.conf import settings      
from .forms import JoinForm
from .pdf_utils import fill_pdf
from django.http import JsonResponse
from django.db import connection
import os

@login_required
def db_test_view(request):
    return HttpResponse("DB 테스트 뷰입니다.")

@login_required
def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            # 폼에는 postcode/address_detail이 없을 수 있으므로 직접 주입
            join_info = form.save(commit=False)
            join_info.postcode = request.POST.get('postcode', '').strip()
            join_info.address_detail = request.POST.get('address_detail', '').strip()
            # 이메일 선택항목이면 빈 문자열을 None으로 정리(선택)
            if not join_info.email:
                join_info.email = None
            join_info.save()

            # ✅ 도로명 + 상세주소 결합 (상세주소가 있을 때만 “, ” 추가)
            base_addr = (join_info.address or '').strip()
            detail = (join_info.address_detail or '').strip()
            combined_address = f"{base_addr}, {detail}" if detail else base_addr

            # 템플릿 경로
            pdf_template_path = os.path.join(settings.BASE_DIR, 'static', 'pdf', 'template.pdf')

            # PDF에 전달할 데이터
            data = {
                "name": join_info.name,
                "ssn": join_info.ssn,
                "address": combined_address,      # ✅ 결합된 주소
                "phone": join_info.phone,
                "email": join_info.email or '',
                "postcode": join_info.postcode or '',
                "address_detail": detail,         # 필요 시 유지
            }

            # PDF 생성
            filled_pdf_path = fill_pdf(pdf_template_path, data)

            # 다운로드 응답
            with open(filled_pdf_path, 'rb') as f:
                pdf_data = f.read()

            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{join_info.name}_가입신청서.pdf"'

            # 임시파일 삭제(선택)
            try:
                os.remove(filled_pdf_path)
            except Exception as e:
                print(f"[임시파일 삭제 실패]: {e}")

            return response

        # 폼 유효성 실패 시
        return render(request, 'join/join_form.html', {'form': form})

    # GET
    form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})