import json
import os

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required, not_inactive_required

from .forms import ManualForm
from .models import Manual, ManualBlock, ManualSection, ManualBlockAttachment


# ============================================================
# Common helpers (공통 모듈화)
# ============================================================

def _to_str(v) -> str:
    return str(v or "").strip()


def _is_digits(v) -> bool:
    return str(v or "").isdigit()


def _json_body(request) -> dict:
    """
    request.body(JSON)를 안전하게 dict로 파싱
    실패 시 {} 반환
    """
    try:
        return json.loads((request.body or b"").decode("utf-8"))
    except Exception:
        return {}


def _ok(data=None):
    payload = {"ok": True}
    if isinstance(data, dict):
        payload.update(data)
    return JsonResponse(payload)


def _fail(message: str, status: int = 400):
    return JsonResponse({"ok": False, "message": message}, status=status)


def _require_superuser(user) -> bool:
    return getattr(user, "grade", "") == "superuser"


def _manual_accessible_or_denied(request, m: Manual):
    """
    ✅ 매뉴얼 접근 권한 체크
    - admin_only=True: superuser/main_admin만
    - is_published=False: superuser만
    """
    grade = getattr(request.user, "grade", "")

    if m.admin_only and grade not in ("superuser", "main_admin"):
        return render(request, "no_permission_popup.html")
    if (not m.is_published) and grade != "superuser":
        return render(request, "no_permission_popup.html")
    return None


def _ensure_default_section(m: Manual) -> ManualSection:
    """
    ✅ 섹션이 하나도 없을 경우 기본 섹션 1개 생성
    - 화면이 비어버리는 상황 방지
    """
    first = m.sections.order_by("sort_order", "id").first()
    if first:
        return first
    return ManualSection.objects.create(manual=m, sort_order=1, title="")


def _attachment_to_dict(a: ManualBlockAttachment) -> dict:
    return {
        "id": a.id,
        "name": a.original_name or os.path.basename(a.file.name),
        "url": a.file.url if a.file else "",
        "size": a.size or 0,
    }


def _block_to_dict(b: ManualBlock) -> dict:
    """
    프런트에서 즉시 DOM 업데이트 가능한 형태로 블록 데이터 직렬화
    (이미지 + 첨부파일 포함)
    """
    return {
        "id": b.id,
        "section_id": b.section_id,
        "content": b.content,
        "image_url": b.image.url if b.image else "",
        "attachments": [_attachment_to_dict(a) for a in b.attachments.all().order_by("created_at", "id")],
    }


# ============================================================
# Pages
# ============================================================

@not_inactive_required
def manual_list(request):
    """
    ✅ 매뉴얼 목록
    - 직원전용(is_published=False)은 superuser만
    - 관리자전용(admin_only=True)은 superuser/main_admin만
    """
    qs = Manual.objects.all()
    grade = getattr(request.user, "grade", "")

    if grade != "superuser":
        qs = qs.filter(is_published=True)

    if grade not in ("superuser", "main_admin"):
        qs = qs.filter(admin_only=False)

    qs = qs.order_by("sort_order", "-updated_at")
    return render(request, "manual/manual_list.html", {"manuals": qs})


@not_inactive_required
def manual_detail(request, pk):
    """
    ✅ 매뉴얼 상세 (섹션 + 블록)
    - 섹션 0개면 기본 섹션 생성
    """
    m = get_object_or_404(Manual, pk=pk)

    denied = _manual_accessible_or_denied(request, m)
    if denied:
        return denied

    _ensure_default_section(m)

    sections = (
        m.sections
        .prefetch_related("blocks", "blocks__attachments")
        .order_by("sort_order", "created_at")
    )

    return render(request, "manual/manual_detail.html", {"m": m, "sections": sections})


@grade_required(["superuser"])
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


@grade_required(["superuser"])
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


# ============================================================
# Manual AJAX
# ============================================================

@require_POST
@login_required
def manual_create_ajax(request):
    """✅ superuser만: 모달 기반 생성"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    title = _to_str(payload.get("title"))
    access = _to_str(payload.get("access") or "normal")

    if not title:
        return _fail("매뉴얼 이름을 입력해주세요.", 400)
    if len(title) > 80:
        return _fail("매뉴얼 이름은 80자 이하여야 합니다.", 400)
    if access not in ("normal", "admin", "staff"):
        return _fail("공개 범위 값이 올바르지 않습니다.", 400)

    admin_only = (access == "admin")
    staff_only = (access == "staff")   # 직원전용=비공개
    manual = Manual.objects.create(
        title=title,
        admin_only=admin_only,
        is_published=(not staff_only),
    )
    return _ok({"redirect_url": reverse("manual:manual_detail", args=[manual.pk])})


@require_POST
@login_required
def manual_update_title_ajax(request):
    """✅ superuser만: 매뉴얼 타이틀 단건 수정"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    mid = payload.get("id")
    title = _to_str(payload.get("title"))

    if not _is_digits(mid):
        return _fail("id 값이 올바르지 않습니다.", 400)
    if not title:
        return _fail("제목을 입력해주세요.", 400)
    if len(title) > 80:
        return _fail("제목은 80자 이하여야 합니다.", 400)

    m = get_object_or_404(Manual, id=int(mid))
    m.title = title
    m.save(update_fields=["title", "updated_at"])
    return _ok({"title": m.title})


@require_POST
@login_required
def manual_bulk_update_ajax(request):
    """✅ superuser만: 여러 매뉴얼 title/access 일괄 업데이트"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    items = payload.get("items") or []
    if not isinstance(items, list):
        return _fail("items 형식이 올바르지 않습니다.", 400)

    def access_to_flags(access: str):
        if access == "admin":
            return True, True
        if access == "staff":
            return False, False
        return False, True

    updated = []
    with transaction.atomic():
        for it in items:
            mid = it.get("id")
            title = _to_str(it.get("title"))
            access = _to_str(it.get("access") or "normal")

            if not _is_digits(mid):
                return _fail("id 값이 올바르지 않습니다.", 400)
            if not title:
                return _fail("제목은 비워둘 수 없습니다.", 400)
            if len(title) > 80:
                return _fail("제목은 80자 이하여야 합니다.", 400)
            if access not in ("normal", "admin", "staff"):
                return _fail("공개 범위 값이 올바르지 않습니다.", 400)

            m = get_object_or_404(Manual, id=int(mid))
            admin_only, is_published = access_to_flags(access)
            m.title = title
            m.admin_only = admin_only
            m.is_published = is_published
            m.save(update_fields=["title", "admin_only", "is_published", "updated_at"])

            updated.append({
                "id": m.id,
                "title": m.title,
                "admin_only": m.admin_only,
                "is_published": m.is_published,
            })

    return _ok({"updated": updated})


@require_POST
@login_required
def manual_reorder_ajax(request):
    """✅ superuser만: 매뉴얼 목록 정렬 저장"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    ordered_ids = payload.get("ordered_ids") or []

    if (not isinstance(ordered_ids, list)) or (not all(_is_digits(x) for x in ordered_ids)):
        return _fail("ordered_ids 형식이 올바르지 않습니다.", 400)

    ordered_ids = [int(x) for x in ordered_ids]
    exist_count = Manual.objects.filter(id__in=ordered_ids).count()
    if exist_count != len(ordered_ids):
        return _fail("존재하지 않는 매뉴얼이 포함되어 있습니다.", 400)

    with transaction.atomic():
        for idx, mid in enumerate(ordered_ids, start=1):
            Manual.objects.filter(id=mid).update(sort_order=idx)

    return _ok()


@require_POST
@login_required
def manual_delete_ajax(request):
    """✅ superuser만: 매뉴얼 삭제"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    mid = payload.get("id")
    if not _is_digits(mid):
        return _fail("id 값이 올바르지 않습니다.", 400)

    get_object_or_404(Manual, id=int(mid)).delete()
    return _ok()


# ============================================================
# Section AJAX
# ============================================================

@require_POST
@login_required
def manual_section_add_ajax(request):
    """✅ superuser만: 섹션(카드) 추가"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    manual_id = payload.get("manual_id")
    if not _is_digits(manual_id):
        return _fail("manual_id가 올바르지 않습니다.", 400)

    m = get_object_or_404(Manual, pk=int(manual_id))
    last = m.sections.order_by("-sort_order", "-id").first()
    next_order = (last.sort_order if last else 0) + 1
    sec = ManualSection.objects.create(manual=m, sort_order=next_order, title="")

    return _ok({
        "section": {
            "id": sec.id,
            "sort_order": sec.sort_order,
            "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
    })


@require_POST
@login_required
def manual_section_title_update_ajax(request):
    """✅ superuser만: 섹션 소제목(title) 수정"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    section_id = payload.get("section_id")
    title = _to_str(payload.get("title"))

    if not _is_digits(section_id):
        return _fail("section_id가 올바르지 않습니다.", 400)
    if len(title) > 120:
        return _fail("소제목은 최대 120자까지 가능합니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    sec.title = title
    sec.save(update_fields=["title", "updated_at"])

    return _ok({
        "section": {
            "id": sec.id,
            "title": sec.title,
            "updated_at": sec.updated_at.strftime("%Y-%m-%d %H:%M"),
        }
    })


@require_POST
@login_required
def manual_section_delete_ajax(request):
    """✅ superuser만: 섹션(카드) 삭제"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    section_id = payload.get("section_id")
    if not _is_digits(section_id):
        return _fail("section_id가 올바르지 않습니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    manual = sec.manual
    sec.delete()

    new_section = None
    if manual.sections.count() == 0:
        created = _ensure_default_section(manual)
        new_section = {"id": created.id, "title": created.title or ""}

    return _ok({"new_section": new_section})


@require_POST
@login_required
def manual_section_reorder_ajax(request):
    """✅ superuser만: 섹션(카드) 순서 저장"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    manual_id = payload.get("manual_id")
    section_ids = payload.get("section_ids") or []

    if not _is_digits(manual_id) or not isinstance(section_ids, list):
        return _fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualSection.objects.filter(manual_id=int(manual_id))
    existing = set(qs.values_list("id", flat=True))
    cleaned = [int(sid) for sid in section_ids if _is_digits(sid) and int(sid) in existing]

    with transaction.atomic():
        for idx, sid in enumerate(cleaned, start=1):
            ManualSection.objects.filter(id=sid).update(sort_order=idx)

    return _ok()


# ============================================================
# Block AJAX
# ============================================================

@require_POST
def manual_block_add_ajax(request):
    """✅ superuser만: 블록 추가 (FormData: multipart)"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    manual_id = request.POST.get("manual_id")
    section_id = request.POST.get("section_id")
    content = request.POST.get("content", "")

    if not (_is_digits(manual_id) and _is_digits(section_id)):
        return _fail("요청값이 올바르지 않습니다.", 400)

    try:
        sec = ManualSection.objects.get(id=int(section_id), manual_id=int(manual_id))
    except ManualSection.DoesNotExist:
        return _fail("섹션을 찾을 수 없습니다.", 404)

    image = request.FILES.get("image")

    last_order = ManualBlock.objects.filter(section=sec).count()
    b = ManualBlock.objects.create(
        manual=sec.manual,  # ⚠️ 중복 구조지만 기존 호환 위해 유지
        section=sec,
        content=content,
        image=image if image else None,
        sort_order=last_order + 1,
    )

    # prefetch 대신 즉시 참조(새 블록은 attachments 없음)
    return _ok({"block": _block_to_dict(b)})


@require_POST
def manual_block_update_ajax(request):
    """✅ superuser만: 블록 수정 (FormData: multipart)"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    block_id = request.POST.get("block_id")
    content = request.POST.get("content", "")
    remove_image = request.POST.get("remove_image", "0")
    image = request.FILES.get("image")

    if not _is_digits(block_id):
        return _fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(
        ManualBlock.objects.select_related("section__manual").prefetch_related("attachments"),
        id=int(block_id),
    )

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

    return _ok({"block": _block_to_dict(b)})


@require_POST
@login_required
def manual_block_delete_ajax(request):
    """✅ superuser만: 블록 삭제"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    block_id = payload.get("block_id")
    if not _is_digits(block_id):
        return _fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(ManualBlock.objects.prefetch_related("attachments"), pk=int(block_id))
    b.delete()  # 블록 delete()에서 이미지 삭제 + attachments cascade(각 attachment delete에서 파일 삭제)
    return _ok()


@require_POST
@login_required
def manual_block_reorder_ajax(request):
    """✅ superuser만: 블록 순서 저장(섹션 단위)"""
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    section_id = payload.get("section_id")
    block_ids = payload.get("block_ids") or []

    if not _is_digits(section_id) or not isinstance(block_ids, list):
        return _fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualBlock.objects.filter(section_id=int(section_id))
    existing = set(qs.values_list("id", flat=True))
    cleaned = [int(bid) for bid in block_ids if _is_digits(bid) and int(bid) in existing]

    with transaction.atomic():
        for idx, bid in enumerate(cleaned, start=1):
            ManualBlock.objects.filter(id=bid).update(sort_order=idx)

    return _ok()


# ============================================================
# Block Attachments AJAX (NEW)
# ============================================================

@require_POST
def manual_block_attachment_upload_ajax(request):
    """
    ✅ superuser만: 블록 첨부 업로드 (FormData: multipart)
    POST(form-data): block_id, file
    return: { attachment: {id, name, url, size} }
    """
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    block_id = request.POST.get("block_id")
    upfile = request.FILES.get("file")

    if not _is_digits(block_id):
        return _fail("block_id가 올바르지 않습니다.", 400)
    if not upfile:
        return _fail("업로드할 파일이 없습니다.", 400)

    # ✅ 기본 용량 제한(원하면 조정)
    MAX_SIZE = 20 * 1024 * 1024  # 20MB
    if upfile.size and upfile.size > MAX_SIZE:
        return _fail("파일 용량은 최대 20MB까지 가능합니다.", 400)

    b = get_object_or_404(ManualBlock, pk=int(block_id))

    a = ManualBlockAttachment.objects.create(
        block=b,
        file=upfile,
        original_name=_to_str(getattr(upfile, "name", "")),
        size=int(getattr(upfile, "size", 0) or 0),
    )

    return _ok({"attachment": _attachment_to_dict(a)})


@require_POST
@login_required
def manual_block_attachment_delete_ajax(request):
    """
    ✅ superuser만: 첨부 삭제 (JSON)
    payload: { attachment_id: number }
    """
    if not _require_superuser(request.user):
        return _fail("권한이 없습니다.", 403)

    payload = _json_body(request)
    attachment_id = payload.get("attachment_id")
    if not _is_digits(attachment_id):
        return _fail("attachment_id가 올바르지 않습니다.", 400)

    a = get_object_or_404(ManualBlockAttachment, pk=int(attachment_id))
    a.delete()  # model delete()에서 파일도 삭제
    return _ok()
