# django_ma/manual/views.py

"""
manual/views.py (final refactor)

원칙
- URL/함수명/응답형태 유지(기존 JS/템플릿 호환)
- 반복되는 파싱/검증/권한/직렬화는 utils.py로 이동
- 상수는 constants.py로 이동
- "왜 필요한가" 중심 주석 보강
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required, not_inactive_required

from .constants import MANUAL_TITLE_MAX_LEN, MAX_ATTACHMENT_SIZE, SECTION_TITLE_MAX_LEN
from .forms import ManualForm
from .models import Manual, ManualBlock, ManualBlockAttachment, ManualSection
from .utils import (
    access_to_flags,
    block_to_dict,
    ensure_default_section,
    ensure_superuser_or_403,
    fail,
    is_digits,
    json_body,
    manual_accessible_or_denied,
    ok,
    to_str,
)


@grade_required("superuser", "head", "leader", "basic")
def redirect_to_manual(request):
    return redirect("manual:manual_list")


# =============================================================================
# Pages
# =============================================================================

@not_inactive_required
def manual_list(request):
    """
    ✅ 매뉴얼 목록
    - 직원전용(is_published=False)은 superuser만 노출
    - 관리자전용(admin_only=True)은 superuser/head만 노출
    """
    grade = getattr(request.user, "grade", "")

    qs = Manual.objects.all()

    # 직원전용(비공개)은 superuser만
    if grade != "superuser":
        qs = qs.filter(is_published=True)

    # 관리자전용은 superuser/head만
    if grade not in ("superuser", "head"):
        qs = qs.filter(admin_only=False)

    qs = qs.order_by("sort_order", "-updated_at")

    return render(request, "manual/manual_list.html", {"manuals": qs})


@not_inactive_required
def manual_detail(request, pk):
    """
    ✅ 매뉴얼 상세 (섹션 + 블록)
    - 접근권한 체크
    - 섹션 0개면 기본 섹션 생성
    - sections -> blocks -> attachments 까지 prefetch하여 DB 쿼리 최소화
    """
    manual = get_object_or_404(Manual, pk=pk)

    denied = manual_accessible_or_denied(request, manual)
    if denied:
        return denied

    ensure_default_section(manual)

    sections = (
        manual.sections
        .prefetch_related("blocks", "blocks__attachments")
        .order_by("sort_order", "created_at")
    )

    return render(request, "manual/manual_detail.html", {"m": manual, "sections": sections})


@grade_required("superuser")
def manual_create(request):
    """✅ superuser 전용: 폼 기반 생성(관리용)"""
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


@grade_required("superuser")
def manual_edit(request, pk):
    """✅ superuser 전용: 폼 기반 수정(관리용)"""
    obj = get_object_or_404(Manual, pk=pk)

    if request.method == "POST":
        form = ManualForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("manual:manual_detail", pk=obj.pk)
    else:
        form = ManualForm(instance=obj)

    return render(request, "manual/manual_form.html", {"form": form, "mode": "edit", "m": obj})


# =============================================================================
# Manual AJAX
# =============================================================================

@require_POST
@login_required
def manual_create_ajax(request):
    """✅ superuser 전용: 모달 기반 생성"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    title = to_str(payload.get("title"))
    access = to_str(payload.get("access") or "normal")

    if not title:
        return fail("매뉴얼 이름을 입력해주세요.", 400)
    if len(title) > MANUAL_TITLE_MAX_LEN:
        return fail(f"매뉴얼 이름은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)
    if access not in ("normal", "admin", "staff"):
        return fail("공개 범위 값이 올바르지 않습니다.", 400)

    admin_only, is_published = access_to_flags(access)

    manual = Manual.objects.create(
        title=title,
        admin_only=admin_only,
        is_published=is_published,
    )

    return ok({"redirect_url": reverse("manual:manual_detail", args=[manual.pk])})


@require_POST
@login_required
def manual_update_title_ajax(request):
    """✅ superuser 전용: 매뉴얼 타이틀 단건 수정"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    mid = payload.get("id")
    title = to_str(payload.get("title"))

    if not is_digits(mid):
        return fail("id 값이 올바르지 않습니다.", 400)
    if not title:
        return fail("제목을 입력해주세요.", 400)
    if len(title) > MANUAL_TITLE_MAX_LEN:
        return fail(f"제목은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)

    m = get_object_or_404(Manual, id=int(mid))
    m.title = title
    m.save(update_fields=["title", "updated_at"])

    return ok({"title": m.title})


@require_POST
@login_required
def manual_bulk_update_ajax(request):
    """
    ✅ superuser 전용: 여러 매뉴얼 title/access 일괄 업데이트

    payload 예시:
    {
      "items": [
        {"id": 1, "title": "...", "access": "normal|admin|staff"},
        ...
      ]
    }
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    items = payload.get("items") or []

    if not isinstance(items, list):
        return fail("items 형식이 올바르지 않습니다.", 400)

    updated = []

    # 일괄 업데이트는 중간 실패 시 전체 롤백이 안전
    with transaction.atomic():
        for it in items:
            mid = it.get("id")
            title = to_str(it.get("title"))
            access = to_str(it.get("access") or "normal")

            if not is_digits(mid):
                return fail("id 값이 올바르지 않습니다.", 400)
            if not title:
                return fail("제목은 비워둘 수 없습니다.", 400)
            if len(title) > MANUAL_TITLE_MAX_LEN:
                return fail(f"제목은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)
            if access not in ("normal", "admin", "staff"):
                return fail("공개 범위 값이 올바르지 않습니다.", 400)

            m = get_object_or_404(Manual, id=int(mid))
            admin_only, is_published = access_to_flags(access)

            m.title = title
            m.admin_only = admin_only
            m.is_published = is_published
            m.save(update_fields=["title", "admin_only", "is_published", "updated_at"])

            updated.append(
                {
                    "id": m.id,
                    "title": m.title,
                    "admin_only": m.admin_only,
                    "is_published": m.is_published,
                }
            )

    return ok({"updated": updated})


@require_POST
@login_required
def manual_reorder_ajax(request):
    """✅ superuser 전용: 매뉴얼 목록 정렬 저장"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    ordered_ids = payload.get("ordered_ids") or []

    if (not isinstance(ordered_ids, list)) or (not all(is_digits(x) for x in ordered_ids)):
        return fail("ordered_ids 형식이 올바르지 않습니다.", 400)

    ordered_ids = [int(x) for x in ordered_ids]

    # 존재하지 않는 ID가 섞이면 프런트 상태와 불일치 → 방어
    exist_count = Manual.objects.filter(id__in=ordered_ids).count()
    if exist_count != len(ordered_ids):
        return fail("존재하지 않는 매뉴얼이 포함되어 있습니다.", 400)

    with transaction.atomic():
        for idx, mid in enumerate(ordered_ids, start=1):
            Manual.objects.filter(id=mid).update(sort_order=idx)

    return ok()


@require_POST
@login_required
def manual_delete_ajax(request):
    """✅ superuser 전용: 매뉴얼 삭제"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    mid = payload.get("id")

    if not is_digits(mid):
        return fail("id 값이 올바르지 않습니다.", 400)

    get_object_or_404(Manual, id=int(mid)).delete()
    return ok()


# =============================================================================
# Section AJAX
# =============================================================================

@require_POST
@login_required
def manual_section_add_ajax(request):
    """✅ superuser 전용: 섹션(카드) 추가"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    manual_id = payload.get("manual_id")

    if not is_digits(manual_id):
        return fail("manual_id가 올바르지 않습니다.", 400)

    m = get_object_or_404(Manual, pk=int(manual_id))
    last = m.sections.order_by("-sort_order", "-id").first()
    next_order = (last.sort_order if last else 0) + 1

    sec = ManualSection.objects.create(manual=m, sort_order=next_order, title="")

    return ok(
        {
            "section": {
                "id": sec.id,
                "sort_order": sec.sort_order,
                "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
        }
    )


@require_POST
@login_required
def manual_section_title_update_ajax(request):
    """✅ superuser 전용: 섹션 소제목(title) 수정"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")
    title = to_str(payload.get("title"))

    if not is_digits(section_id):
        return fail("section_id가 올바르지 않습니다.", 400)
    if len(title) > SECTION_TITLE_MAX_LEN:
        return fail(f"소제목은 최대 {SECTION_TITLE_MAX_LEN}자까지 가능합니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    sec.title = title
    sec.save(update_fields=["title", "updated_at"])

    return ok(
        {
            "section": {
                "id": sec.id,
                "title": sec.title,
                "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
        }
    )


@require_POST
@login_required
def manual_section_delete_ajax(request):
    """
    ✅ superuser 전용: 섹션(카드) 삭제
    - 마지막 섹션까지 삭제되면 상세 화면이 비어버리므로 기본 섹션을 자동 생성
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")

    if not is_digits(section_id):
        return fail("section_id가 올바르지 않습니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    manual = sec.manual
    sec.delete()

    new_section = None
    if manual.sections.count() == 0:
        created = ensure_default_section(manual)
        new_section = {"id": created.id, "title": created.title or ""}

    return ok({"new_section": new_section})


@require_POST
@login_required
def manual_section_reorder_ajax(request):
    """✅ superuser 전용: 섹션(카드) 순서 저장"""
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    manual_id = payload.get("manual_id")
    section_ids = payload.get("section_ids") or []

    if not is_digits(manual_id) or not isinstance(section_ids, list):
        return fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualSection.objects.filter(manual_id=int(manual_id))
    existing = set(qs.values_list("id", flat=True))

    # 프런트 배열 중 "해당 manual에 속한 섹션"만 반영(혼입 방지)
    cleaned = [int(sid) for sid in section_ids if is_digits(sid) and int(sid) in existing]

    with transaction.atomic():
        for idx, sid in enumerate(cleaned, start=1):
            ManualSection.objects.filter(id=sid).update(sort_order=idx)

    return ok()


# =============================================================================
# Block AJAX (multipart 포함)
# =============================================================================

@require_POST
@login_required
def manual_block_add_ajax(request):
    """
    ✅ superuser 전용: 블록 추가 (FormData: multipart)
    POST(form-data): manual_id, section_id, content, image(optional)
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    manual_id = request.POST.get("manual_id")
    section_id = request.POST.get("section_id")
    content = request.POST.get("content", "")
    image = request.FILES.get("image")

    if not (is_digits(manual_id) and is_digits(section_id)):
        return fail("요청값이 올바르지 않습니다.", 400)

    try:
        sec = ManualSection.objects.get(id=int(section_id), manual_id=int(manual_id))
    except ManualSection.DoesNotExist:
        return fail("섹션을 찾을 수 없습니다.", 404)

    # sort_order는 “섹션 내 블록 개수 + 1” (기존 로직 유지)
    last_order = ManualBlock.objects.filter(section=sec).count()

    b = ManualBlock.objects.create(
        manual=sec.manual,     # ⚠️ 중복 구조지만 기존 호환 위해 유지
        section=sec,
        content=content,
        image=image if image else None,
        sort_order=last_order + 1,
    )

    return ok({"block": block_to_dict(b)})


@require_POST
@login_required
def manual_block_update_ajax(request):
    """
    ✅ superuser 전용: 블록 수정 (FormData: multipart)
    POST(form-data): block_id, content, remove_image(0|1), image(optional)
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    block_id = request.POST.get("block_id")
    content = request.POST.get("content", "")
    remove_image = request.POST.get("remove_image", "0")
    image = request.FILES.get("image")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(
        ManualBlock.objects.select_related("section__manual").prefetch_related("attachments"),
        id=int(block_id),
    )

    # 파일 교체/삭제는 트랜잭션으로 묶어 일관성 강화
    with transaction.atomic():
        b.content = content

        if remove_image == "1":
            if b.image:
                b.image.delete(save=False)
            b.image = None

        if image:
            if b.image:
                b.image.delete(save=False)
            b.image = image

        b.save()

    return ok({"block": block_to_dict(b)})


@require_POST
@login_required
def manual_block_delete_ajax(request):
    """
    ✅ superuser 전용: 블록 삭제 (JSON)
    payload: { block_id: number }
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    block_id = payload.get("block_id")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(
        ManualBlock.objects.prefetch_related("attachments"),
        pk=int(block_id),
    )
    # 블록 delete()에서 이미지 삭제 + attachments cascade(각 attachment delete에서 파일 삭제)
    b.delete()

    return ok()


@require_POST
@login_required
def manual_block_reorder_ajax(request):
    """
    ✅ superuser 전용: 블록 순서 저장(섹션 단위)
    payload: { section_id: number, block_ids: [id, ...] }
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    section_id = payload.get("section_id")
    block_ids = payload.get("block_ids") or []

    if not is_digits(section_id) or not isinstance(block_ids, list):
        return fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualBlock.objects.filter(section_id=int(section_id))
    existing = set(qs.values_list("id", flat=True))
    cleaned = [int(bid) for bid in block_ids if is_digits(bid) and int(bid) in existing]

    with transaction.atomic():
        for idx, bid in enumerate(cleaned, start=1):
            ManualBlock.objects.filter(id=bid).update(sort_order=idx)

    return ok()


# =============================================================================
# Block Attachments AJAX
# =============================================================================

@require_POST
@login_required
def manual_block_attachment_upload_ajax(request):
    """
    ✅ superuser 전용: 블록 첨부 업로드 (FormData: multipart)
    POST(form-data): block_id, file
    return: { attachment: {id, name, url, size} }
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    block_id = request.POST.get("block_id")
    upfile = request.FILES.get("file")

    if not is_digits(block_id):
        return fail("block_id가 올바르지 않습니다.", 400)
    if not upfile:
        return fail("업로드할 파일이 없습니다.", 400)

    if upfile.size and upfile.size > MAX_ATTACHMENT_SIZE:
        mb = int(MAX_ATTACHMENT_SIZE / (1024 * 1024))
        return fail(f"파일 용량은 최대 {mb}MB까지 가능합니다.", 400)

    b = get_object_or_404(ManualBlock, pk=int(block_id))

    a = ManualBlockAttachment.objects.create(
        block=b,
        file=upfile,
        original_name=to_str(getattr(upfile, "name", "")),
        size=int(getattr(upfile, "size", 0) or 0),
    )

    # utils에 있는 직렬화 형태를 그대로 유지하기 위해 block_to_dict 대신 dict 직접 구성
    from .utils import attachment_to_dict
    return ok({"attachment": attachment_to_dict(a)})


@require_POST
@login_required
def manual_block_attachment_delete_ajax(request):
    """
    ✅ superuser 전용: 첨부 삭제 (JSON)
    payload: { attachment_id: number }
    """
    denied = ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = json_body(request)
    attachment_id = payload.get("attachment_id")

    if not is_digits(attachment_id):
        return fail("attachment_id가 올바르지 않습니다.", 400)

    a = get_object_or_404(ManualBlockAttachment, pk=int(attachment_id))
    # model delete()에서 파일도 삭제
    a.delete()

    return ok()

def rules_home(request): return render(request, "manual/rules_home.html")