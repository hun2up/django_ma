# django_ma/commission/views/api_deposit_impl.py
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.models import CustomUser

# TODO: 기존 구현이 있다면 여기로 옮기세요.
# from commission.models import DepositSummary, DepositSurety, DepositOther
# from accounts.search_api import search_users (또는 너 SSOT search_user API)


def _fmt_date(d) -> str:
    """
    날짜 표시 포맷 (템플릿의 join_date_display/retire_date_display에 사용)
    - 값이 없으면 '-' (템플릿 기본 정책과 동일)
    """
    try:
        return d.strftime("%Y-%m-%d") if d else "-"
    except Exception:
        return "-"


def _user_to_payload(u: CustomUser) -> dict:
    """
    Deposit Home 템플릿/JS(data-bind)에서 기대하는 user payload.

    템플릿에서 사용되는 키:
      - target.id / target.name / target.part / target.branch
      - target.join_date_display / target.retire_date_display

    ✅ join/retire display는 CustomUser.enter/quit 기반으로 내려준다.
    """
    return {
        "id": u.id,
        "name": getattr(u, "name", "") or "",
        "part": getattr(u, "part", "") or "",
        "branch": getattr(u, "branch", "") or "",
        # enter/quit → display
        "join_date_display": _fmt_date(getattr(u, "enter", None)),
        "retire_date_display": _fmt_date(getattr(u, "quit", None)),
        # (선택) 원본도 같이 제공(다른 화면 재사용 대비)
        "enter": getattr(u, "enter", None).isoformat() if getattr(u, "enter", None) else "",
        "quit": getattr(u, "quit", None).isoformat() if getattr(u, "quit", None) else "",
    }

@require_GET
def search_user(request):
    """
    (Fallback) 대상자 검색 API
    - 실제 운영은 accounts:api_search_user(SSOT)를 사용 중일 수 있음.
    - 그래도 deposit 쪽 구현이 비어있으면 테스트/호환이 불편하므로 최소 구현 제공.
    """
    q = (request.GET.get("q") or request.GET.get("keyword") or "").strip()
    if not q:
        return JsonResponse({"ok": True, "results": []})

    qs = (
        CustomUser.objects.all()
        .only("id", "name", "part", "branch", "enter", "quit")
        .order_by("id")
    )

    # name 우선, 그 다음 id 문자열 포함(사번/PK)
    qs = qs.filter(name__icontains=q) | qs.filter(id__icontains=q)

    results = [_user_to_payload(u) for u in qs[:20]]
    return JsonResponse({"ok": True, "results": results})


@require_GET
def api_user_detail(request):
    """
    Deposit Home - 사용자 상세
    - deposit_home.js가 data-user-detail-url 로 호출
    - 템플릿은 data-bind="target.*" 로 바인딩

    파라미터:
     - user: 사용자 PK(프로젝트에서 CustomUser PK가 문자열/사번일 수도 있음)
      - (fallback) id / emp_id 등으로도 받을 수 있게 확장 가능
    """
    user_id = (request.GET.get("user") or request.GET.get("id") or "").strip()
    if not user_id:
        return JsonResponse({"ok": False, "message": "user 파라미터가 필요합니다."}, status=400)

    u = (
        CustomUser.objects.filter(pk=user_id)
        .only("id", "name", "part", "branch", "enter", "quit")
       .first()
    )
    if not u:
        return JsonResponse({"ok": False, "message": "대상자를 찾지 못했습니다."}, status=404)

    # ✅ 응답 키는 템플릿/JS와 호환되게 data/user 둘 다 제공
    payload = _user_to_payload(u)
    return JsonResponse({"ok": True, "data": payload, "user": payload})


@require_GET
def api_deposit_summary(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_deposit_surety_list(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_deposit_other_list(request):
    return JsonResponse({"ok": True, "rows": []})


@require_GET
def api_support_pdf(request):
    return JsonResponse({"ok": False, "message": "Not implemented"}, status=501)
