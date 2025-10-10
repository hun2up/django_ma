from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings  # ⬅ 이거 있어야 BASE_DIR 사용 가능
import os

from .forms import JoinForm
from .pdf_utils import fill_pdf  # fill_pdf 함수는 utils 파일에 정의

# join/views.py
from django.http import JsonResponse
from django.db import connection

def db_test_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        return JsonResponse({"db_connection": "ok", "result": row[0]})
    except Exception as e:
        return JsonResponse({"db_connection": "error", "message": str(e)})

def join_form(request):
    if request.method == 'POST':
        form = JoinForm(request.POST)
        if form.is_valid():
            join_info = form.save()

            # ✅ 템플릿 PDF 경로 지정 (static/pdf/template.pdf)
            pdf_template_path = os.path.join(settings.BASE_DIR, 'static', 'pdf', 'template.pdf')

            # ✅ DB에서 저장된 사용자 정보 dict로 추출
            data = {
                "name": join_info.name,
                "ssn": join_info.ssn,
                "address": join_info.address,
                "phone": join_info.phone,
            }

            # ✅ PDF 생성
            filled_pdf_path = fill_pdf(pdf_template_path, data)

            # ✅ 생성된 PDF를 HTTP 응답으로 반환
            with open(filled_pdf_path, 'rb') as f:
                pdf_data = f.read()

            response = HttpResponse(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="입력된정보.pdf"'

            # ✅ 임시파일 삭제 (선택)
            os.remove(filled_pdf_path)

            return response
    else:
        form = JoinForm()
    return render(request, 'join/join_form.html', {'form': form})
