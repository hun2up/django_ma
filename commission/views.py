# django_ma/commission/views.py
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from accounts.decorators import grade_required
from django.db import transaction
from django.core.files.storage import FileSystemStorage
from accounts.models import CustomUser
from django.db.models import Q
from .models import Payment


# ✅ 기본 수수료 페이지 접속 시 → 채권관리 페이지로 자동 이동
@grade_required(['superuser'])
def redirect_to_deposit(request):
    return redirect('deposit_home')


# ✅ 채권관리 페이지 (메인)
@grade_required(['superuser'])
def deposit_home(request):
    """
    채권관리 메인 페이지
    - user 파라미터로 선택된 사용자의 인적사항 표시
    - Payment DB의 최종지급액 데이터를 함께 표시
    """
    user_id = request.GET.get('user')
    context = {'target': None, 'payment': None}

    if user_id:
        try:
            target = CustomUser.objects.get(id=user_id)
            fields = dir(target)

            # ✅ 입사일/퇴사일 필드 자동 감지
            join_field_name = next((f for f in fields if 'join' in f or 'hire' in f), None)
            retire_field_name = next((f for f in fields if 'retire' in f or 'quit' in f or 'leave' in f), None)

            join_value = getattr(target, join_field_name, None) if join_field_name else None
            retire_value = getattr(target, retire_field_name, None) if retire_field_name else None

            target.join_date_display = join_value.strftime('%Y-%m-%d') if join_value else "-"
            target.retire_date_display = retire_value.strftime('%Y-%m-%d') if retire_value else "재직중"

            # ✅ Payment DB에서 해당 설계사 최종지급액 조회
            payment = Payment.objects.filter(user_id=user_id).first()

            context.update({
                'target': target,
                'payment': payment.amount if payment else None
            })

        except CustomUser.DoesNotExist:
            pass  # 기본 context 유지 (공란 상태)

    return render(request, 'commission/deposit_home.html', context)


# ✅ 지원신청서 (제작중)
@grade_required(['superuser'])
def support_home(request):
    return render(request, 'commission/support_home.html')


# ✅ 수수료결재 (제작중)
@grade_required(['superuser'])
def approval_home(request):
    return render(request, 'commission/approval_home.html')


# ✅ 대상자 검색
@grade_required(['superuser'])
def search_user(request):
    q = request.GET.get('q', '').strip()
    results = []

    if q:
        queryset = CustomUser.objects.filter(Q(id__icontains=q) | Q(name__icontains=q))
        results = [{'id': u.id, 'name': u.name, 'branch': u.branch} for u in queryset]

    return JsonResponse({'results': results})


# ✅ 엑셀 업로드
@csrf_exempt
@grade_required(['superuser'])
def upload_excel(request):
    """
    [최종지급액] 엑셀 업로드 (1행 머릿글 + 2행 무시 버전)
    - 1행: 헤더, 2행: 삭제, 3행부터 데이터
    - '사번', '최종지급액' 컬럼 자동 탐지
    - Payment DB 신규/갱신 반영
    """
    if request.method != 'POST':
        return JsonResponse({'message': '잘못된 요청 방식입니다.'}, status=400)

    if 'excel_file' not in request.FILES:
        return JsonResponse({'message': '엑셀 파일이 전달되지 않았습니다.'}, status=400)

    upload_type = request.POST.get('upload_type')
    excel_file = request.FILES['excel_file']

    print(f"=== [디버그] 업로드 타입: {upload_type}")
    print(f"=== [디버그] 파일명: {excel_file.name}")
    print(f"=== [디버그] POST keys: {list(request.POST.keys())}")
    print(f"=== [디버그] FILES keys: {list(request.FILES.keys())}")

    if upload_type != "최종지급액":
        return JsonResponse({'message': '현재는 [최종지급액] 업로드만 지원됩니다.'}, status=400)

    try:
        # ✅ 파일 임시 저장
        fs = FileSystemStorage()
        filename = fs.save(excel_file.name, excel_file)
        file_path = fs.path(filename)

        # ✅ 엑셀 읽기 (1행 헤더, 2행 제거)
        df = pd.read_excel(file_path, header=0)
        print("📊 원본 컬럼:", list(df.columns))

        if len(df) > 1:
            df = df.drop(index=1).reset_index(drop=True)
            print("🧹 2행 제거 완료")

        # ✅ '사번', '최종지급' 컬럼 자동 탐색
        user_col = next((c for c in df.columns if "사번" in str(c)), None)
        pay_col = next((c for c in df.columns if "최종" in str(c) and "지급" in str(c)), None)

        if not user_col or not pay_col:
            return JsonResponse({
                'message': '⚠️ 업로드 파일을 확인해주세요. (사번 또는 최종지급액 컬럼을 찾을 수 없습니다.)'
            }, status=400)

        df = df[[user_col, pay_col]]
        df.columns = ['user_id', 'amount']

        print(f"📄 사용된 컬럼: {user_col}, {pay_col}")
        print("📈 데이터 샘플:\n", df.head(3))

        # ✅ 숫자형 변환 (콤마 제거 + NaN 처리)
        df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce').astype('Int64')
        df['amount'] = (
            df['amount']
            .astype(str)
            .str.replace(',', '', regex=True)
            .replace(['', 'nan', 'NaN', None], '0')
            .astype(float)
        )

        # ✅ 실제 DB 반영
        with transaction.atomic():
            count = 0
            for _, row in df.dropna(subset=['user_id']).iterrows():
                user_id = int(row['user_id'])
                amount = int(row['amount'])
                try:
                    Payment.objects.update_or_create(
                        user_id=user_id,
                        defaults={'amount': amount}
                    )
                    count += 1
                except Exception as e:
                    print(f"❌ 행 처리 중 오류 (user_id={user_id}, amount={amount}): {e}")
                    continue

        print(f"✅ [디버그] 업로드 완료: 총 {count}행 처리됨 ===")
        return JsonResponse({'message': f'✅ {count}건 업로드 완료 (payment 테이블 반영)'})

    except Exception as e:
        print("❌ 업로드 중 오류:", e)
        return JsonResponse({'message': f'⚠️ 업로드 실패: {str(e)}'}, status=500)
