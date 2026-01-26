# partner/views/subadmin.py
# ------------------------------------------------------------
# ✅ sub-admin(leader) 추가/삭제 API (원본 하단 스냅샷 기반)
# - 원본 파일은 중간이 잘렸으므로, 'branch 권한 체크' 부분은 TODO로 남김
# - 기존 안전정책 유지:
#   1) CustomUser.grade 변경은 update()로(시그널/후처리 우회)
#   2) SubAdminTemp는 삭제 금지 (팀A/B/C 보존), level만 초기화
# ------------------------------------------------------------

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from accounts.decorators import grade_required
from accounts.models import CustomUser
from partner.models import SubAdminTemp


def _to_str(v):
    return ("" if v is None else str(v)).strip()


@require_POST
@login_required
@grade_required("superuser", "head")
@transaction.atomic
def ajax_add_sub_admin(request):
    user_id = _to_str(request.POST.get("user_id") or request.POST.get("id"))
    if not user_id:
        return JsonResponse({"ok": False, "error": "user_id가 없습니다."}, status=400)

    try:
        u = CustomUser.objects.select_for_update().get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({"ok": False, "error": "사용자를 찾을 수 없습니다."}, status=404)

    # TODO: branch 권한 체크 (원본에서 "... (branch 권한 체크 동일)" 로 주석 처리되어 있었음)
    # - head는 자기 지점만 승격 가능
    # - superuser는 제한 없음
    if request.user.grade == "head":
        if (u.branch or "").strip() and (request.user.branch or "").strip() and (u.branch != request.user.branch):
            return JsonResponse({"ok": False, "error": "다른 지점 사용자는 추가할 수 없습니다."}, status=403)

    if u.grade in ("resign", "inactive"):
        return JsonResponse({"ok": False, "error": "퇴사/비활성 사용자는 추가할 수 없습니다."}, status=400)

    changed = (u.grade != "leader")
    u.grade = "leader"
    u.save(update_fields=["grade"])

    sa, created = SubAdminTemp.objects.get_or_create(
        user=u,
        defaults={
            "name": _to_str(u.name) or "-",
            "branch": _to_str(u.branch) or "-",
            "part": _to_str(u.part) or "-",
            "grade": "leader",
            "position": "-",
            "team_a": "-",
            "team_b": "-",
            "team_c": "-",
            "level": "-",
        },
    )

    # ✅ 이미 존재하면 팀A/B/C는 그대로 두고, 기본 메타만 최신화
    updates = {}
    if (sa.name or "").strip() != (u.name or "-"):
        updates["name"] = u.name or "-"
    if (sa.branch or "").strip() != (u.branch or "-"):
        updates["branch"] = u.branch or "-"
    if (sa.part or "").strip() != (u.part or "-"):
        updates["part"] = u.part or "-"
    if (sa.grade or "").strip() != "leader":
        updates["grade"] = "leader"
    if updates:
        SubAdminTemp.objects.filter(pk=sa.pk).update(**updates)

    return JsonResponse(
        {
            "ok": True,
            "changed": changed,
            "user": {"id": u.id, "name": u.name, "branch": _to_str(u.branch), "part": _to_str(u.part), "grade": u.grade},
        }
    )


@require_POST
@transaction.atomic
def ajax_delete_subadmin(request):
    user = request.user
    if user.grade not in ("superuser", "head"):
        return JsonResponse({"ok": False, "error": "권한이 없습니다."}, status=403)

    user_id = (request.POST.get("user_id") or "").strip()
    if not user_id:
        return JsonResponse({"ok": False, "error": "user_id가 필요합니다."}, status=400)

    target = get_object_or_404(CustomUser, pk=user_id)

    # ✅ 1) CustomUser.grade 변경: save() 금지 (signals / 후처리 우회)
    CustomUser.objects.filter(pk=target.pk).update(grade="basic")

    # ✅ 2) SubAdminTemp는 삭제 금지, team_a/b/c 건드리지 않기
    sa_qs = SubAdminTemp.objects.select_for_update().filter(user=target)
    if sa_qs.exists():
        sa_qs.update(
            grade="basic",
            level="-",  # ✅ 핵심: level만 초기화
            name=(target.name or "-"),
            part=(target.part or "-"),
            branch=(target.branch or "-"),
            # team_a/team_b/team_c 는 update에 포함하지 않음 -> 그대로 유지
        )

    return JsonResponse({"ok": True})
