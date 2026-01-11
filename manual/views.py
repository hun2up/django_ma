# django_ma/manual/templates/manual/views.py

import json
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from accounts.decorators import not_inactive_required, grade_required
from .models import Manual
from .forms import ManualForm


@not_inactive_required
def manual_list(request):
    qs = Manual.objects.all()

    grade = getattr(request.user, "grade", "")

    # ✅ 직원전용(=is_published=False) : superuser만 볼 수 있음
    if grade != "superuser":
        qs = qs.filter(is_published=True)

    # ✅ 관리자전용(admin_only=True) : superuser/main_admin만 볼 수 있음
    if grade not in ("superuser", "main_admin"):
        qs = qs.filter(admin_only=False)

    # ✅ 정렬 반영
    qs = qs.order_by("sort_order", "-updated_at")

    return render(request, "manual/manual_list.html", {"manuals": qs})


@not_inactive_required
def manual_detail(request, pk):
    m = get_object_or_404(Manual, pk=pk)

    grade = getattr(request.user, "grade", "")

    # ✅ 관리자전용: superuser/main_admin만
    if m.admin_only and grade not in ("superuser", "main_admin"):
        return render(request, "no_permission_popup.html")

    # ✅ 직원전용(=비공개): superuser만
    if (not m.is_published) and grade != "superuser":
        return render(request, "no_permission_popup.html")

    return render(request, "manual/manual_detail.html", {"m": m})

# django_ma/manual/views.py

@require_POST
@login_required
def manual_create_ajax(request):
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    title = (payload.get("title") or "").strip()
    access = (payload.get("access") or "normal").strip()  # ✅ normal/admin/staff

    if not title:
        return JsonResponse({"ok": False, "message": "매뉴얼 이름을 입력해주세요."}, status=400)
    if len(title) > 80:
        return JsonResponse({"ok": False, "message": "매뉴얼 이름은 80자 이하여야 합니다."}, status=400)
    if access not in ("normal", "admin", "staff"):
        return JsonResponse({"ok": False, "message": "공개 범위 값이 올바르지 않습니다."}, status=400)

    # ✅ access만으로 최종 결정 (payload의 admin_only/staff_only는 무시)
    admin_only = (access == "admin")
    staff_only = (access == "staff")  # 직원전용 = is_published False

    manual = Manual.objects.create(
        title=title,
        admin_only=admin_only,
        is_published=(not staff_only),
    )

    redirect_url = reverse("manual:manual_detail", args=[manual.pk])
    return JsonResponse({"ok": True, "redirect_url": redirect_url})

@require_POST
@login_required
def manual_update_title_ajax(request):
    """superuser만: 매뉴얼 타이틀 수정"""
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    mid = payload.get("id")
    title = (payload.get("title") or "").strip()

    if not str(mid).isdigit():
        return JsonResponse({"ok": False, "message": "id 값이 올바르지 않습니다."}, status=400)
    if not title:
        return JsonResponse({"ok": False, "message": "제목을 입력해주세요."}, status=400)
    if len(title) > 80:
        return JsonResponse({"ok": False, "message": "제목은 80자 이하여야 합니다."}, status=400)

    m = get_object_or_404(Manual, id=int(mid))
    m.title = title
    m.save(update_fields=["title", "updated_at"])

    return JsonResponse({"ok": True, "title": m.title})

@require_POST
@login_required
def manual_reorder_ajax(request):
    """superuser만: manual_id 배열 순서대로 sort_order 저장"""
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    ordered_ids = payload.get("ordered_ids") or []
    if not isinstance(ordered_ids, list) or not all(str(x).isdigit() for x in ordered_ids):
        return JsonResponse({"ok": False, "message": "ordered_ids 형식이 올바르지 않습니다."}, status=400)

    ordered_ids = [int(x) for x in ordered_ids]

    # 존재 검증
    exist_count = Manual.objects.filter(id__in=ordered_ids).count()
    if exist_count != len(ordered_ids):
        return JsonResponse({"ok": False, "message": "존재하지 않는 매뉴얼이 포함되어 있습니다."}, status=400)

    with transaction.atomic():
        # 1부터 순서 부여
        for idx, mid in enumerate(ordered_ids, start=1):
            Manual.objects.filter(id=mid).update(sort_order=idx)

    return JsonResponse({"ok": True})


@require_POST
@login_required
def manual_delete_ajax(request):
    """superuser만: 매뉴얼 삭제"""
    if getattr(request.user, "grade", "") != "superuser":
        return JsonResponse({"ok": False, "message": "권한이 없습니다."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    mid = payload.get("id")
    if not str(mid).isdigit():
        return JsonResponse({"ok": False, "message": "id 값이 올바르지 않습니다."}, status=400)

    m = get_object_or_404(Manual, id=int(mid))
    m.delete()
    return JsonResponse({"ok": True})


@grade_required(["superuser"])
def manual_create(request):
    if request.method == "POST":
        form = ManualForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author = request.user
            obj.save()
            return redirect("manual:manual_detail", pk=obj.pk)
    else:
        form = ManualForm()

    return render(request, "manual/manual_form.html", {"form": form, "mode": "create"})

@grade_required(["superuser"])
def manual_edit(request, pk):
    obj = get_object_or_404(Manual, pk=pk)

    if request.method == "POST":
        form = ManualForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("manual:manual_detail", pk=obj.pk)
    else:
        form = ManualForm(instance=obj)

    return render(request, "manual/manual_form.html", {"form": form, "mode": "edit", "m": obj})
