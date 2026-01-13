"""
manual/views.py (refactor)

목표
- 기능별로 “구역(helpers / pages / ajax)” 재정렬
- 반복되는 검증/권한 체크/파싱 로직을 공통화
- 주석을 ‘왜/무엇을’ 중심으로 보강해서 유지보수성 향상
- 기존 API/템플릿/JS와의 호환을 최대한 유지

주의
- 일부 함수는 @login_required가 빠져 있어도, 실제로는 superuser 체크로 막히지만
  CSRF/인증 관점에서 명시적으로 @login_required를 붙여주는 게 안전합니다.
  (아래에서는 기존 구조를 최대한 유지하면서, 위험도가 높은 multipart 업로드 계열에는 login_required를 붙였습니다.)
"""

import json
import os

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required, not_inactive_required

from .forms import ManualForm
from .models import Manual, ManualBlock, ManualSection, ManualBlockAttachment


# ============================================================================
# Constants
# ============================================================================

MANUAL_TITLE_MAX_LEN = 80
SECTION_TITLE_MAX_LEN = 120
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20MB (원하면 조정)


# ============================================================================
# Common helpers (공통 유틸)
# - 문자열/숫자 검증, JSON 파싱, 응답 헬퍼
# - 권한 체크 및 공통 접근 제어
# - 직렬화(프런트 즉시 렌더링용)
# ============================================================================

def _to_str(v) -> str:
    """None/공백 입력을 안전하게 문자열로 정규화"""
    return str(v or "").strip()


def _is_digits(v) -> bool:
    """int로 변환 가능한 숫자 문자열인지 체크"""
    return str(v or "").isdigit()


def _json_body(request) -> dict:
    """
    request.body(JSON)를 안전하게 dict로 파싱
    - 파싱 실패/빈 바디: {}
    """
    try:
        return json.loads((request.body or b"").decode("utf-8"))
    except Exception:
        return {}


def _ok(data=None):
    """통일된 성공 응답"""
    payload = {"ok": True}
    if isinstance(data, dict):
        payload.update(data)
    return JsonResponse(payload)


def _fail(message: str, status: int = 400):
    """통일된 실패 응답"""
    return JsonResponse({"ok": False, "message": message}, status=status)


def _is_superuser(user) -> bool:
    """grade 기반 superuser 판정(프로젝트 컨벤션 유지)"""
    return getattr(user, "grade", "") == "superuser"


def _ensure_superuser_or_403(request):
    """
    ✅ superuser가 아니면 즉시 403 반환용 헬퍼
    - 각 AJAX에서 동일 패턴 반복을 줄이기 위함
    """
    if not _is_superuser(request.user):
        return _fail("권한이 없습니다.", 403)
    return None


def _manual_accessible_or_denied(request, manual: Manual):
    """
    ✅ 매뉴얼 접근 권한 체크
    - admin_only=True: superuser/main_admin만 접근
    - is_published=False: superuser만 접근

    반환:
    - 접근 가능: None
    - 접근 불가: no_permission_popup.html 렌더 결과
    """
    grade = getattr(request.user, "grade", "")

    if manual.admin_only and grade not in ("superuser", "main_admin"):
        return render(request, "no_permission_popup.html")

    if (not manual.is_published) and grade != "superuser":
        return render(request, "no_permission_popup.html")

    return None


def _ensure_default_section(manual: Manual) -> ManualSection:
    """
    ✅ 섹션이 하나도 없을 경우 기본 섹션 1개 생성
    - 상세 화면이 완전히 비어버리는 상황 방지
    """
    first = manual.sections.order_by("sort_order", "id").first()
    if first:
        return first
    return ManualSection.objects.create(manual=manual, sort_order=1, title="")


def _attachment_to_dict(a: ManualBlockAttachment) -> dict:
    """
    첨부파일을 프런트가 즉시 렌더링 가능한 dict로 변환
    """
    return {
        "id": a.id,
        "name": a.original_name or os.path.basename(a.file.name),
        "url": a.file.url if a.file else "",
        "size": a.size or 0,
    }


def _block_to_dict(b: ManualBlock) -> dict:
    """
    블록을 프런트가 즉시 DOM 업데이트 가능한 dict로 변환
    - 이미지 + 첨부파일 포함
    """
    return {
        "id": b.id,
        "section_id": b.section_id,
        "content": b.content,
        "image_url": b.image.url if b.image else "",
        "attachments": [
            _attachment_to_dict(a)
            for a in b.attachments.all().order_by("created_at", "id")
        ],
    }


def _access_to_flags(access: str):
    """
    access 문자열(normal/admin/staff) -> (admin_only, is_published) 변환
    - normal: (False, True)
    - admin : (True,  True)
    - staff : (False, False)  # 직원전용=비공개
    """
    if access == "admin":
        return True, True
    if access == "staff":
        return False, False
    return False, True


# ============================================================================
# Pages (템플릿 렌더링)
# ============================================================================

@not_inactive_required
def manual_list(request):
    """
    ✅ 매뉴얼 목록
    - 직원전용(is_published=False)은 superuser만 노출
    - 관리자전용(admin_only=True)은 superuser/main_admin만 노출
    """
    grade = getattr(request.user, "grade", "")

    qs = Manual.objects.all()

    # 직원전용(비공개)은 superuser만
    if grade != "superuser":
        qs = qs.filter(is_published=True)

    # 관리자전용은 superuser/main_admin만
    if grade not in ("superuser", "main_admin"):
        qs = qs.filter(admin_only=False)

    qs = qs.order_by("sort_order", "-updated_at")

    # NOTE:
    # 기존 코드에 section_qs / manuals prefetch가 남아 있었지만,
    # 실제 render에는 qs만 넘겨서 prefetch 결과를 사용하지 않았습니다.
    # -> 유지보수 관점에서 혼란만 주므로 제거(필요 시 템플릿에서 sections를 쓰게 되면 다시 추가)
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

    denied = _manual_accessible_or_denied(request, manual)
    if denied:
        return denied

    _ensure_default_section(manual)

    sections = (
        manual.sections
        .prefetch_related("blocks", "blocks__attachments")
        .order_by("sort_order", "created_at")
    )

    return render(request, "manual/manual_detail.html", {"m": manual, "sections": sections})


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


# ============================================================================
# Manual AJAX (매뉴얼 CRUD/정렬/일괄수정)
# ============================================================================

@require_POST
@login_required
def manual_create_ajax(request):
    """✅ superuser 전용: 모달 기반 생성"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    title = _to_str(payload.get("title"))
    access = _to_str(payload.get("access") or "normal")

    if not title:
        return _fail("매뉴얼 이름을 입력해주세요.", 400)
    if len(title) > MANUAL_TITLE_MAX_LEN:
        return _fail(f"매뉴얼 이름은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)
    if access not in ("normal", "admin", "staff"):
        return _fail("공개 범위 값이 올바르지 않습니다.", 400)

    admin_only, is_published = _access_to_flags(access)

    manual = Manual.objects.create(
        title=title,
        admin_only=admin_only,
        is_published=is_published,
    )

    return _ok({"redirect_url": reverse("manual:manual_detail", args=[manual.pk])})


@require_POST
@login_required
def manual_update_title_ajax(request):
    """✅ superuser 전용: 매뉴얼 타이틀 단건 수정"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    mid = payload.get("id")
    title = _to_str(payload.get("title"))

    if not _is_digits(mid):
        return _fail("id 값이 올바르지 않습니다.", 400)
    if not title:
        return _fail("제목을 입력해주세요.", 400)
    if len(title) > MANUAL_TITLE_MAX_LEN:
        return _fail(f"제목은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)

    m = get_object_or_404(Manual, id=int(mid))
    m.title = title
    m.save(update_fields=["title", "updated_at"])

    return _ok({"title": m.title})


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
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    items = payload.get("items") or []

    if not isinstance(items, list):
        return _fail("items 형식이 올바르지 않습니다.", 400)

    updated = []

    # 일괄 업데이트는 중간 실패 시 전체 롤백이 안전
    with transaction.atomic():
        for it in items:
            mid = it.get("id")
            title = _to_str(it.get("title"))
            access = _to_str(it.get("access") or "normal")

            if not _is_digits(mid):
                return _fail("id 값이 올바르지 않습니다.", 400)
            if not title:
                return _fail("제목은 비워둘 수 없습니다.", 400)
            if len(title) > MANUAL_TITLE_MAX_LEN:
                return _fail(f"제목은 {MANUAL_TITLE_MAX_LEN}자 이하여야 합니다.", 400)
            if access not in ("normal", "admin", "staff"):
                return _fail("공개 범위 값이 올바르지 않습니다.", 400)

            m = get_object_or_404(Manual, id=int(mid))
            admin_only, is_published = _access_to_flags(access)

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

    return _ok({"updated": updated})


@require_POST
@login_required
def manual_reorder_ajax(request):
    """✅ superuser 전용: 매뉴얼 목록 정렬 저장"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    ordered_ids = payload.get("ordered_ids") or []

    if (not isinstance(ordered_ids, list)) or (not all(_is_digits(x) for x in ordered_ids)):
        return _fail("ordered_ids 형식이 올바르지 않습니다.", 400)

    ordered_ids = [int(x) for x in ordered_ids]

    # 존재하지 않는 ID가 섞이면 프런트 상태와 불일치 → 방어
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
    """✅ superuser 전용: 매뉴얼 삭제"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    mid = payload.get("id")

    if not _is_digits(mid):
        return _fail("id 값이 올바르지 않습니다.", 400)

    get_object_or_404(Manual, id=int(mid)).delete()
    return _ok()


# ============================================================================
# Section AJAX (섹션 카드 CRUD/정렬)
# ============================================================================

@require_POST
@login_required
def manual_section_add_ajax(request):
    """✅ superuser 전용: 섹션(카드) 추가"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    manual_id = payload.get("manual_id")

    if not _is_digits(manual_id):
        return _fail("manual_id가 올바르지 않습니다.", 400)

    m = get_object_or_404(Manual, pk=int(manual_id))
    last = m.sections.order_by("-sort_order", "-id").first()
    next_order = (last.sort_order if last else 0) + 1

    sec = ManualSection.objects.create(manual=m, sort_order=next_order, title="")

    return _ok(
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
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    section_id = payload.get("section_id")
    title = _to_str(payload.get("title"))

    if not _is_digits(section_id):
        return _fail("section_id가 올바르지 않습니다.", 400)
    if len(title) > SECTION_TITLE_MAX_LEN:
        return _fail(f"소제목은 최대 {SECTION_TITLE_MAX_LEN}자까지 가능합니다.", 400)

    sec = get_object_or_404(ManualSection, pk=int(section_id))
    sec.title = title
    sec.save(update_fields=["title", "updated_at"])

    return _ok(
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
    - 마지막 섹션까지 삭제되면, 상세 화면이 비어버리므로 기본 섹션을 자동 생성
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

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
    """✅ superuser 전용: 섹션(카드) 순서 저장"""
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    manual_id = payload.get("manual_id")
    section_ids = payload.get("section_ids") or []

    if not _is_digits(manual_id) or not isinstance(section_ids, list):
        return _fail("요청값이 올바르지 않습니다.", 400)

    qs = ManualSection.objects.filter(manual_id=int(manual_id))
    existing = set(qs.values_list("id", flat=True))

    # 프런트가 보내준 배열 중 "해당 manual에 속한 섹션"만 반영(혼입 방지)
    cleaned = [int(sid) for sid in section_ids if _is_digits(sid) and int(sid) in existing]

    with transaction.atomic():
        for idx, sid in enumerate(cleaned, start=1):
            ManualSection.objects.filter(id=sid).update(sort_order=idx)

    return _ok()


# ============================================================================
# Block AJAX (블록 CRUD/정렬) + 이미지 처리
# - multipart(FormData) 요청은 JSON 파싱이 아니라 request.POST / request.FILES 사용
# ============================================================================

@require_POST
@login_required
def manual_block_add_ajax(request):
    """
    ✅ superuser 전용: 블록 추가 (FormData: multipart)
    POST(form-data): manual_id, section_id, content, image(optional)
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

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

    # sort_order는 “섹션 내 블록 개수 + 1”로 부여(단순/호환)
    last_order = ManualBlock.objects.filter(section=sec).count()

    b = ManualBlock.objects.create(
        manual=sec.manual,  # ⚠️ 중복 구조지만 기존 호환 위해 유지
        section=sec,
        content=content,
        image=image if image else None,
        sort_order=last_order + 1,
    )

    # 새 블록은 attachments가 없으므로 즉시 직렬화로 반환
    return _ok({"block": _block_to_dict(b)})


@require_POST
@login_required
def manual_block_update_ajax(request):
    """
    ✅ superuser 전용: 블록 수정 (FormData: multipart)
    POST(form-data): block_id, content, remove_image(0|1), image(optional)
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

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

    # 이미지 교체/삭제는 파일 시스템 작업이 포함되므로 트랜잭션으로 묶어 안전성 강화
    with transaction.atomic():
        b.content = content

        if remove_image == "1":
            if b.image:
                b.image.delete(save=False)
            b.image = None

        # 새 이미지가 오면 기존 이미지 삭제 후 교체
        if image:
            if b.image:
                b.image.delete(save=False)
            b.image = image

        b.save()

    return _ok({"block": _block_to_dict(b)})


@require_POST
@login_required
def manual_block_delete_ajax(request):
    """
    ✅ superuser 전용: 블록 삭제 (JSON)
    payload: { block_id: number }
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    block_id = payload.get("block_id")

    if not _is_digits(block_id):
        return _fail("block_id가 올바르지 않습니다.", 400)

    b = get_object_or_404(ManualBlock.objects.prefetch_related("attachments"), pk=int(block_id))
    # 블록 delete()에서 이미지 삭제 + attachments cascade(각 attachment delete에서 파일 삭제)
    b.delete()

    return _ok()


@require_POST
@login_required
def manual_block_reorder_ajax(request):
    """
    ✅ superuser 전용: 블록 순서 저장(섹션 단위)
    payload: { section_id: number, block_ids: [id, ...] }
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

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


# ============================================================================
# Block Attachments AJAX (첨부 업로드/삭제)
# ============================================================================

@require_POST
@login_required
def manual_block_attachment_upload_ajax(request):
    """
    ✅ superuser 전용: 블록 첨부 업로드 (FormData: multipart)
    POST(form-data): block_id, file
    return: { attachment: {id, name, url, size} }
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    block_id = request.POST.get("block_id")
    upfile = request.FILES.get("file")

    if not _is_digits(block_id):
        return _fail("block_id가 올바르지 않습니다.", 400)
    if not upfile:
        return _fail("업로드할 파일이 없습니다.", 400)

    # 기본 용량 제한(원하면 조정)
    if upfile.size and upfile.size > MAX_ATTACHMENT_SIZE:
        mb = int(MAX_ATTACHMENT_SIZE / (1024 * 1024))
        return _fail(f"파일 용량은 최대 {mb}MB까지 가능합니다.", 400)

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
    ✅ superuser 전용: 첨부 삭제 (JSON)
    payload: { attachment_id: number }
    """
    denied = _ensure_superuser_or_403(request)
    if denied:
        return denied

    payload = _json_body(request)
    attachment_id = payload.get("attachment_id")

    if not _is_digits(attachment_id):
        return _fail("attachment_id가 올바르지 않습니다.", 400)

    a = get_object_or_404(ManualBlockAttachment, pk=int(attachment_id))
    # model delete()에서 파일도 삭제
    a.delete()

    return _ok()
