# django_ma/dash/views.py
from __future__ import annotations

import pandas as pd
from datetime import datetime
from typing import Optional

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from accounts.models import CustomUser
from accounts.decorators import grade_required
from .models import SalesRecord


# -----------------------------
# 보험사 분류 (손보/생보)
# -----------------------------
NONLIFE_INSURERS = {
    '현대해상', 'DB손보', 'KB손보', '메리츠화재', '한화손보', '롯데손보', '흥국화재',
    '삼성화재', 'AIG손보', 'MG손보', '농협손보', '하나손보'
}
LIFE_INSURERS = {
    'ABL생명', '삼성생명', '신한라이프', '하나생명', 'IBK연금', 'DB생명', 'iM라이프',
    'KB라이프생명', 'NH농협생명', '라이나생명', 'KDB생명', '미래에셋', '처브라이프',
    '한화생명', '카디프생명', '동양생명', '메트라이프', '흥국생명', '푸본현대생명', '교보생명'
}

# 엑셀 필수 컬럼
REQUIRED_COLS = [
    '소속', '영업가족', '설계사', '설계사CD', '보험사', '증권번호', '계약자', '주피',
    '보험시작', '보험종기', '납입방법', '영수일자', '영수금', '보험사 상품코드', '보험사 상품명'
]


# -----------------------------
# 페이지 라우팅
# -----------------------------
@grade_required(["superuser", "main_admin"])
def redirect_to_sales(request):
    return redirect('dash_sales')


@grade_required(["superuser", "main_admin"])
def dash_sales(request):
    # 기본 월도: 이번달(서버 기준)
    default_ym = datetime.now().strftime('%Y-%m')

    ym = (request.GET.get("ym") or default_ym).strip()
    life_nl = (request.GET.get("life_nl") or "").strip()          # 손보/생보/기타
    insurer = (request.GET.get("insurer") or "").strip()          # 보험사 정확히 일치
    q = (request.GET.get("q") or "").strip()                      # 증권번호/계약자/설계사/사번 검색
    page = request.GET.get("page", "1")

    qs = SalesRecord.objects.all()

    if ym:
        qs = qs.filter(ym=ym)
    if life_nl:
        qs = qs.filter(life_nl=life_nl)
    if insurer:
        qs = qs.filter(insurer=insurer)
    if q:
        qs = qs.filter(
            Q(policy_no__icontains=q)
            | Q(contractor__icontains=q)
            | Q(name_snapshot__icontains=q)
            | Q(emp_id_snapshot__icontains=q)
            | Q(user__id__icontains=q)
            | Q(user__name__icontains=q)
        )

    qs = qs.select_related("user").order_by("-updated_at")

    # 페이징
    paginator = Paginator(qs, 50)  # 페이지당 50건
    page_obj = paginator.get_page(page)

    # 상단 표시용(필터 상태 유지)
    context = {
        "filter_ym": ym,
        "filter_life_nl": life_nl,
        "filter_insurer": insurer,
        "filter_q": q,

        "total_count": qs.count(),
        "page_obj": page_obj,
    }
    return render(request, "dash/dash_sales.html", context)



@grade_required(["superuser", "main_admin"])
def dash_recruit(request):
    return render(request, 'dash/dash_recruit.html')


@grade_required(["superuser", "main_admin"])
def dash_retention(request):
    return render(request, 'dash/dash_retention.html')


# -----------------------------
# 유틸
# -----------------------------
def _to_date(v) -> Optional[datetime.date]:
    if pd.isna(v) or v == '':
        return None
    try:
        dt = pd.to_datetime(v, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.date()
    except Exception:
        return None


def _to_str_emp_id(v) -> Optional[str]:
    if pd.isna(v) or v == '':
        return None
    try:
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        s = str(v).strip()
        if s.endswith('.0'):
            s = s[:-2]
        return s
    except Exception:
        return str(v).strip()


def _life_nl(insurer: str) -> str:
    insurer = (insurer or '').strip()
    if insurer in NONLIFE_INSURERS:
        return '손보'
    if insurer in LIFE_INSURERS:
        return '생보'
    return '기타'


def _json_err(message: str, status: int = 400):
    return JsonResponse({'ok': False, 'message': message}, status=status)


# -----------------------------
# 업로드 API
# -----------------------------
@grade_required(["superuser", "main_admin"])
@require_POST
def upload_sales_excel(request):
    """
    업로드 처리:
    - CustomUser: id(설계사CD) 기준으로 part/branch/name 업데이트 또는 생성
    - SalesRecord: policy_no(증권번호) PK 기준 update_or_create (upsert)
    - life_nl: 보험사명 기준 손보/생보/기타 자동 부여
    - ym: 영수일자 기준 YYYY-MM (없으면 서버 현재월)
    """
    f = request.FILES.get('excel_file')
    if not f:
        return _json_err('엑셀 파일(excel_file)이 없습니다.', 400)

    try:
        df = pd.read_excel(f)
    except Exception as e:
        return _json_err(f'엑셀 읽기 실패: {e}', 400)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return _json_err(f'필수 컬럼이 없습니다: {missing}', 400)

    # 증권번호 없는 행 제거
    df = df[~df['증권번호'].isna()].copy()

    created_users = 0
    updated_users = 0
    upserted_rows = 0
    skipped_rows = 0

    with transaction.atomic():
        for _, r in df.iterrows():
            policy_no = str(r.get('증권번호')).strip()
            insurer = str(r.get('보험사')).strip() if not pd.isna(r.get('보험사')) else ''
            emp_id = _to_str_emp_id(r.get('설계사CD'))
            name = str(r.get('설계사')).strip() if not pd.isna(r.get('설계사')) else None
            part = str(r.get('소속')).strip() if not pd.isna(r.get('소속')) else None
            branch = str(r.get('영업가족')).strip() if not pd.isna(r.get('영업가족')) else None

            # 필수값 체크
            if not policy_no or policy_no.lower() == 'nan':
                skipped_rows += 1
                continue
            if not emp_id:
                skipped_rows += 1
                continue
            if not insurer:
                skipped_rows += 1
                continue

            # ym 계산(영수일자 기준)
            rd = _to_date(r.get('영수일자'))
            ym = rd.strftime('%Y-%m') if rd else datetime.now().strftime('%Y-%m')

            # 1) CustomUser upsert
            user_defaults = {}
            if name:
                user_defaults['name'] = name
            if part:
                user_defaults['part'] = part
            if branch:
                user_defaults['branch'] = branch

            user, created = CustomUser.objects.update_or_create(
                id=emp_id,
                defaults=user_defaults
            )
            if created:
                created_users += 1
            else:
                updated_users += 1

            # 2) receipt_amount 안전 변환
            receipt_amount = r.get('영수금')
            try:
                if pd.isna(receipt_amount) or receipt_amount == '':
                    receipt_amount = None
                else:
                    receipt_amount = int(receipt_amount)
            except Exception:
                receipt_amount = None

            # 3) SalesRecord upsert
            SalesRecord.objects.update_or_create(
                policy_no=policy_no,
                defaults={
                    'user': user,

                    'part_snapshot': part,
                    'branch_snapshot': branch,
                    'name_snapshot': name,
                    'emp_id_snapshot': emp_id,

                    'insurer': insurer,
                    'contractor': (str(r.get('계약자')).strip() if not pd.isna(r.get('계약자')) else None),
                    'main_premium': (str(r.get('주피')).strip() if not pd.isna(r.get('주피')) else None),

                    'ins_start': _to_date(r.get('보험시작')),
                    'ins_end': _to_date(r.get('보험종기')),
                    'pay_method': (str(r.get('납입방법')).strip() if not pd.isna(r.get('납입방법')) else None),

                    'receipt_date': rd,
                    'receipt_amount': receipt_amount,

                    'product_code': (str(r.get('보험사 상품코드')).strip() if not pd.isna(r.get('보험사 상품코드')) else None),
                    'product_name': (str(r.get('보험사 상품명')).strip() if not pd.isna(r.get('보험사 상품명')) else None),

                    'life_nl': _life_nl(insurer),
                    'ym': ym,
                }
            )
            upserted_rows += 1

    return JsonResponse({
        'ok': True,
        'message': '업로드 완료',
        'summary': {
            'users_created': created_users,
            'users_updated': updated_users,
            'rows_upserted': upserted_rows,
            'rows_skipped': skipped_rows,
            'rows_in_file': int(len(df)),
        }
    })
