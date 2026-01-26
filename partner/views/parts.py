# partner/views/parts.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models.functions import Trim

from accounts.decorators import grade_required
from accounts.models import CustomUser


@login_required
@grade_required("superuser")
def ajax_fetch_channels(request):
    exclude_list = ["", "-", None]
    channels = (
        CustomUser.objects.exclude(channel__in=exclude_list)
        .values_list("channel", flat=True)
        .distinct()
        .order_by("channel")
    )
    return JsonResponse({"channels": list(channels)})


@login_required
@grade_required("superuser")
def ajax_fetch_parts(request):
    """
    ✅ channel 기반 part 목록 (distinct)
    - channel 파라미터가 있으면 해당 channel 안에서만 part 추출
    - part에 '센터'가 포함된 항목은 제외
    - part가 NULL/빈 문자열/공백만 있는 값은 제외
    """
    channel = (request.GET.get("channel") or "").strip()

    qs = (
        CustomUser.objects
        .exclude(part__isnull=True)
        .exclude(part__exact="")
        .exclude(part__icontains="센터")   # ✅ '센터' 포함 부서 제외
        .annotate(part_trim=Trim("part"))
        .exclude(part_trim__exact="")     # ✅ 공백만 있는 값 제거
    )

    if channel:
        qs = qs.filter(channel__iexact=channel)

    # ✅ trim 기준으로 distinct + 정렬된 part 리스트
    parts = (
        qs.values_list("part_trim", flat=True)
          .distinct()
          .order_by("part_trim")
    )

    return JsonResponse({"parts": list(parts)})


@login_required
@grade_required("superuser")
def ajax_fetch_branches(request):
    """
    ✅ channel + part 기반 branch 목록
    """
    channel = (request.GET.get("channel") or "").strip()
    part = (request.GET.get("part") or "").strip()
    if not part:
        return JsonResponse({"branches": []})

    exclude_list = ["", "-", None]
    qs = (
        CustomUser.objects
        .filter(part__iexact=part)
        .exclude(branch__in=exclude_list)
    )

    if channel:
        qs = qs.filter(channel__iexact=channel)

    qs = qs.annotate(branch_trim=Trim("branch")).exclude(branch_trim__exact="")
    branches = qs.values_list("branch_trim", flat=True).distinct().order_by("branch_trim")
    
    return JsonResponse({"branches": list(branches)})
