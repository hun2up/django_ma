from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
import os

from .models import JoinInfo
from .forms import JoinForm
from .pdf_utils import fill_pdf


@login_required
def db_test_view(request):
    return HttpResponse("DB 테스트 뷰입니다.")


@login_required
def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            # ✅ join_info 객체 생성, DB 저장은 보류
            join_info = form.save(commit=False)

            # ✅ cleaned_data 기반으로 안전하게 값 추출
            postcode = form.cleaned_data.get('postcode', '').strip()
            address = form.cleaned_data.get('address', '').strip()
            address_detail = form.cleaned_data.get('address_detail', '').strip()
            email = form.cleaned_data.get('email') or None  # 선택 항목 정리

            # 값 주입
            join_info.postcode = postcode
            join_info.address = address
            join_info.address_detail = address_detail
            join_info.email = email
            join_info.save()

            # ✅ 전체 주소 조합
            combined_address = f"{address}, {address_detail}" if address_detail else address

            # ✅ PDF 템플릿 경로 설정
            # ✅ PDF 템플릿 경로 설정
            pdf_template_path = os.path.join(settings.BASE_DIR, 'static', 'pdf', 'template.pdf')

            # ✅ PDF 데이터 구성
            data = {
                "name": join_info.name,
                "ssn": join_info.ssn,
                "address": combined_address,
                "phone": join_info.phone,
                "email": email or '',
                "postcode": postcode,
                "address_detail": address_detail,
            }

            # ✅ PDF 생성 함수 호출
            filled_pdf_path = fill_pdf(pdf_template_path, data)

            # ✅ 응답으로 PDF 전송
            with open(filled_pdf_path, 'rb') as f:
                pdf_data = f.read()

            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{join_info.name}_가입신청서.pdf"'

            # ✅ 임시 파일 삭제 시도
            try:
                os.remove(filled_pdf_path)
            except Exception as e:
                print(f"[임시파일 삭제 실패]: {e}")

            return response  # PDF 파일 다운로드

        # 폼 검증 실패 → 에러 포함해서 다시 렌더링
        return render(request, 'join/join_form.html', {'form': form})

    # GET 요청 → 빈 폼 렌더링
    form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})


# ✅ 추가: success_view (누락되어 있던 함수)
@login_required
def success_view(request):
    """PDF 생성 완료 또는 가입 성공 후 보여줄 안내 페이지"""
    return render(request, 'join/success.html')
