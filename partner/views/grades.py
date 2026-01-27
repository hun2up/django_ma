# django_ma/partner/views/grades.py
# ------------------------------------------------------------
# ✅ Permission Management (manage_grades + excel upload + datatables api + level update)
# - leader 명단 새로고침 시 유지
# - leader인데 SubAdminTemp 없는 경우 자동 생성
# - signals/승격/강등 상황에서도 팀/직급 덮어쓰기 최소화
# - excel 업로드: 팀/직급만 최신 반영, level/grade는 불필요한 덮어쓰기 금지
# - DataTables 검색: SubAdminTemp 검색도 "현재 범위 사용자"로 제한
# ------------------------------------------------------------

from __future__ import annotations

import traceback
from urllib.parse import urlencode

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from partner.models import SubAdminTemp

from .constants import BRANCH_PARTS
from .utils import find_part_by_branch


MIDDLE_GRADES = ("leader",)
LEVELS = ["-", "A레벨", "B레벨", "C레벨"]


def _to_str(v) -> str:
    return ("" if v is None else str(v)).strip()


def _build_redirect_url(base_name: str, params: dict) -> str:
    base = reverse(base_name)
    clean = {k: _to_str(v) for k, v in (params or {}).items() if _to_str(v)}
    return f"{base}?{urlencode(clean)}" if clean else base


def _ensure_subadmin_temp_for_users(users_qs):
    """
    ✅ leader 사용자 중 SubAdminTemp가 없는 경우 자동 생성.
    - 핵심: team_a/b/c, position 덮어쓰기 금지 (NULL 유지)
    - name/part/branch/grade/level만 최소 생성
    """
    user_ids = list(users_qs.values_list("id", flat=True))
    if not user_ids:
        return

    existing_ids = set(
        SubAdminTemp.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True)
    )
    missing_ids = [uid for uid in user_ids if uid not in existing_ids]
    if not missing_ids:
        return

    missing_users = (
        CustomUser.objects.filter(id__in=missing_ids)
        .only("id", "name", "part", "branch", "grade")
    )

    SubAdminTemp.objects.bulk_create(
        [
            SubAdminTemp(
                user=u,
                name=_to_str(u.name) or "-",
                part=_to_str(u.part) or "-",
                branch=_to_str(u.branch) or "-",
                grade="leader",   # leader 보장
                level="-",
                # team_a/b/c, position은 일부러 설정하지 않음(NULL 유지)
            )
            for u in missing_users
        ],
        ignore_conflicts=True,
    )


@login_required
@grade_required("superuser", "head")
def manage_grades(request):
    user = request.user
    parts = sorted(list(BRANCH_PARTS.keys()))

    selected_channel = _to_str(request.GET.get("channel"))
    selected_part = _to_str(request.GET.get("part"))
    selected_branch = _to_str(request.GET.get("branch"))

    # ✅ leader 기준 집합은 항상 CustomUser에서 만든다.
    leader_base_qs = CustomUser.objects.filter(grade__in=MIDDLE_GRADES, status="재직")

    if user.grade == "superuser":
        if selected_channel and selected_part and selected_branch:
            leader_qs = leader_base_qs.filter(
                channel=selected_channel,
                part=selected_part,
                branch=selected_branch,
            )
            _ensure_subadmin_temp_for_users(leader_qs)

            # ✅ 화면 렌더는 SubAdminTemp 기반
            subadmin_qs = (
                SubAdminTemp.objects.select_related("user")
                .filter(user__in=leader_qs)
                .order_by("name", "user__id")
            )

            users_all = CustomUser.objects.filter(
                channel=selected_channel,
                part=selected_part,
                branch=selected_branch,
                status="재직",
            ).order_by("name", "id")
        else:
            subadmin_qs = SubAdminTemp.objects.none()
            users_all = CustomUser.objects.none()

    else:
        # head: 자신의 지점 고정
        selected_branch = _to_str(user.branch)
        selected_part = find_part_by_branch(selected_branch) or _to_str(user.part)

        leader_qs = leader_base_qs.filter(branch=selected_branch)
        _ensure_subadmin_temp_for_users(leader_qs)

        subadmin_qs = (
            SubAdminTemp.objects.select_related("user")
            .filter(user__in=leader_qs)
            .order_by("name", "user__id")
        )

        users_all = CustomUser.objects.filter(branch=selected_branch, status="재직").order_by("name", "id")

    empty_message_subadmin = "" if subadmin_qs.exists() else "표시할 중간관리자가 없습니다."

    return render(
        request,
        "partner/manage_grades.html",
        {
            "parts": parts,
            "selected_channel": selected_channel or None,
            "selected_part": selected_part or None,
            "selected_branch": selected_branch or None,
            "users_subadmin": subadmin_qs,
            "users_all": users_all,
            "empty_message_subadmin": empty_message_subadmin,
            "levels": LEVELS,
        },
    )


@transaction.atomic
@login_required
@grade_required("superuser", "head")
def upload_grades_excel(request):
    """
    ✅ 권한관리 엑셀 업로드:
    - 목적: 팀/직급 최신 반영
    - 정책:
      - team_a/b/c, position은 업로드 값으로 반영
      - level은 기존값 유지(없으면 "-")
      - grade는 기존값 유지(비어있으면 CustomUser.grade로 채움)
      - name/part/branch는 CustomUser 기준으로 동기화
    """
    redirect_channel = _to_str(request.GET.get("channel"))
    redirect_part = _to_str(request.GET.get("part"))
    redirect_branch = _to_str(request.GET.get("branch"))

    def _redirect():
        return redirect(
            _build_redirect_url(
                "partner:manage_grades",
                {"channel": redirect_channel, "part": redirect_part, "branch": redirect_branch},
            )
        )

    if not (request.method == "POST" and request.FILES.get("excel_file")):
        messages.warning(request, "엑셀 파일을 선택하세요.")
        return _redirect()

    file = request.FILES["excel_file"]

    try:
        df = pd.read_excel(file, sheet_name="업로드").fillna("")
        required_cols = ["사번", "팀A", "팀B", "팀C", "직급", "성명"]
        for col in required_cols:
            if col not in df.columns:
                messages.error(request, f"엑셀에 '{col}' 컬럼이 없습니다.")
                return _redirect()

        # 안전: 불필요 컬럼 제거(있어도 무방)
        for col in ["부서", "지점", "등급", "레벨"]:
            if col in df.columns:
                df = df.drop(columns=[col])

        updated, created = 0, 0

        for _, row in df.iterrows():
            user_id = _to_str(row.get("사번"))
            if not user_id:
                continue

            cu = CustomUser.objects.filter(id=user_id).first()
            if not cu:
                continue

            # ✅ SubAdminTemp 확보
            sa, is_created = SubAdminTemp.objects.get_or_create(
                user=cu,
                defaults={
                    "name": _to_str(cu.name) or "-",
                    "part": _to_str(cu.part) or "-",
                    "branch": _to_str(cu.branch) or "-",
                    "grade": _to_str(cu.grade) or "basic",
                    "level": "-",
                    # ✅ 생성 시에는 업로드값도 반영
                    "team_a": _to_str(row.get("팀A")) or "-",
                    "team_b": _to_str(row.get("팀B")) or "-",
                    "team_c": _to_str(row.get("팀C")) or "-",
                    "position": _to_str(row.get("직급")) or "-",
                },
            )

            if is_created:
                created += 1
                continue

            # ✅ 업데이트: 팀/직급은 업로드값으로 반영, level은 유지
            updates = {
                "name": _to_str(cu.name) or "-",
                "part": _to_str(cu.part) or "-",
                "branch": _to_str(cu.branch) or "-",
                "team_a": _to_str(row.get("팀A")) or "-",
                "team_b": _to_str(row.get("팀B")) or "-",
                "team_c": _to_str(row.get("팀C")) or "-",
                "position": _to_str(row.get("직급")) or "-",
            }

            # grade는 "비어있을 때만" 채움 (덮어쓰기 금지)
            if not _to_str(getattr(sa, "grade", "")):
                updates["grade"] = _to_str(cu.grade) or "basic"

            # level도 "비어있을 때만" 채움 (덮어쓰기 금지)
            if not _to_str(getattr(sa, "level", "")):
                updates["level"] = "-"

            SubAdminTemp.objects.filter(pk=sa.pk).update(**updates)
            updated += 1

        messages.success(request, f"업로드 완료: 신규 {created}건, 수정 {updated}건 반영")

    except Exception as e:
        traceback.print_exc()
        messages.error(request, f"엑셀 처리 중 오류 발생: {e}")

    return _redirect()


@login_required
@grade_required("superuser", "head")
def ajax_users_data(request):
    """✅ DataTables server-side API (범위 제한 + SubAdminTemp 검색 범위 제한)"""
    user = request.user

    # draw/start/length 안전 파싱
    try:
        draw = int(request.GET.get("draw", "1") or "1")
    except ValueError:
        draw = 1

    try:
        start = max(int(request.GET.get("start", 0)), 0)
    except ValueError:
        start = 0

    try:
        length = int(request.GET.get("length", 10))
        if length <= 0:
            length = 10
    except ValueError:
        length = 10

    search = _to_str(request.GET.get("search[value]", ""))
    selected_part = _to_str(request.GET.get("part", ""))
    selected_branch = _to_str(request.GET.get("branch", ""))
    selected_channel = _to_str(request.GET.get("channel", ""))  # superuser일 때 optional 안전

    try:
        # 1) 범위(base_qs) 확정
        if user.grade == "superuser":
            if not selected_part or not selected_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)

            base_qs = CustomUser.objects.filter(part=selected_part, branch=selected_branch, status="재직")
            if selected_channel:
                base_qs = base_qs.filter(channel=selected_channel)

        else:
            fixed_branch = _to_str(user.branch)
            if not fixed_branch:
                return JsonResponse({"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0}, status=200)

            base_qs = CustomUser.objects.filter(branch=fixed_branch, status="재직")

            if not selected_part:
                selected_part = find_part_by_branch(fixed_branch) or _to_str(user.part)

        records_total = base_qs.count()
        qs = base_qs

        # 2) 검색(search) 처리
        if search:
            # ✅ CustomUser 범위 내에서 먼저 매칭되는 id들
            ids_from_custom = list(
                qs.filter(
                    Q(name__icontains=search)
                    | Q(id__icontains=search)
                    | Q(branch__icontains=search)
                    | Q(part__icontains=search)
                ).values_list("id", flat=True)
            )

            # ✅ SubAdminTemp도 "현재 범위 사용자"로 제한해서 검색 (전체 스캔 방지)
            base_ids = list(qs.values_list("id", flat=True))
            ids_from_subadmin = list(
                SubAdminTemp.objects.filter(user_id__in=base_ids).filter(
                    Q(team_a__icontains=search)
                    | Q(team_b__icontains=search)
                    | Q(team_c__icontains=search)
                    | Q(position__icontains=search)
                ).values_list("user_id", flat=True)
            )

            combined_ids = set(ids_from_custom) | set(ids_from_subadmin)
            qs = qs.filter(id__in=combined_ids)

        records_filtered = qs.count()

        # 3) 페이지
        qs = qs.order_by("name", "id")
        page_qs = qs.only("id", "name", "branch", "part")[start : start + length]
        page_ids = [u.id for u in page_qs]

        # 4) SubAdminTemp 매핑
        subadmin_map = {
            str(sa.user_id): {
                "name": _to_str(sa.name),
                "position": _to_str(sa.position) or "-",
                "team_a": _to_str(sa.team_a) or "-",
                "team_b": _to_str(sa.team_b) or "-",
                "team_c": _to_str(sa.team_c) or "-",
                "level": _to_str(sa.level) or "-",
                "grade": _to_str(sa.grade) or "",
            }
            for sa in SubAdminTemp.objects.filter(user_id__in=page_ids)
        }

        data = []
        for u in page_qs:
            sa = subadmin_map.get(str(u.id), {})
            display_name = _to_str(u.name) or sa.get("name") or "-"
            data.append(
                {
                    "part": _to_str(u.part) or "-",
                    "branch": _to_str(u.branch) or "-",
                    "name": display_name,
                    "user_id": u.id,
                    "position": sa.get("position", "-"),
                    "team_a": sa.get("team_a", "-"),
                    "team_b": sa.get("team_b", "-"),
                    "team_c": sa.get("team_c", "-"),
                    "level": sa.get("level", "-"),
                    # grade도 내려주면 프론트에서 활용 가능(필요없으면 제거 가능)
                    "grade": sa.get("grade", "") or _to_str(getattr(u, "grade", "")),
                }
            )

        return JsonResponse(
            {"draw": draw, "data": data, "recordsTotal": records_total, "recordsFiltered": records_filtered},
            status=200,
        )

    except Exception as e:
        traceback.print_exc()
        return JsonResponse(
            {"draw": draw, "data": [], "recordsTotal": 0, "recordsFiltered": 0, "error": str(e)},
            status=200,
        )


@require_POST
@login_required
@grade_required("superuser", "head")
def ajax_update_level(request):
    user_id = _to_str(request.POST.get("user_id"))
    level = _to_str(request.POST.get("level"))

    if level not in LEVELS:
        return JsonResponse({"success": False, "error": "Invalid level"}, status=400)

    try:
        sa = SubAdminTemp.objects.get(user_id=user_id)
        sa.level = level
        sa.save(update_fields=["level"])
        return JsonResponse({"success": True})
    except SubAdminTemp.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"}, status=404)
