# join/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import JoinInfo
from .forms import JoinForm
from .pdf_utils import fill_pdf
from django.http import JsonResponse
from django.db import connection
import os

def db_test_view(request):
    return HttpResponse("DB 테스트 뷰입니다.")

def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            join_info = form.save()

            # ✅ 상세주소와 결합: "도로명주소, 상세주소" (상세주소가 있으면만 콤마 추가)
            base_addr = (join_info.address or "").strip()
            detail = (join_info.address_detail or "").strip()
            combined_address = f"{base_addr}, {detail}" if detail else base_addr

            pdf_template_path = os.path.join('static', 'pdf', 'template.pdf')

            data = {
                "name": join_info.name,
                "ssn": join_info.ssn,
                "address": combined_address,   # ✅ 여기만 결합된 주소로 전달
                "phone": join_info.phone,
                "email": join_info.email or '',
                "postcode": join_info.postcode or '',
                "address_detail": detail,      # 필요시 유지
            }

            filled_pdf_path = fill_pdf(pdf_template_path, data)

            with open(filled_pdf_path, 'rb') as f:
                pdf_data = f.read()

            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{join_info.name}_가입신청서.pdf"'

            try:
                os.remove(filled_pdf_path)
            except Exception as e:
                print(f"[임시파일 삭제 실패]: {e}")

            return response
        else:
            return render(request, 'join/join_form.html', {'form': form})

    form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})