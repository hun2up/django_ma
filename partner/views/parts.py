# partner/views/parts.py

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

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
    """
    channel = (request.GET.get("channel") or "").strip()

    qs = (
        CustomUser.objects.exclude(part__isnull=True)
        .exclude(part__exact="")
    )

    if channel:
        qs = qs.filter(channel__iexact=channel)

    parts = qs.values_list("part", flat=True).distinct().order_by("part")
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

    qs = CustomUser.objects.filter(part__iexact=part).exclude(branch__isnull=True).exclude(branch__exact="")

    if channel:
        qs = qs.filter(channel__iexact=channel)

    branches = qs.values_list("branch", flat=True).distinct().order_by("branch")
    return JsonResponse({"branches": list(branches)})
