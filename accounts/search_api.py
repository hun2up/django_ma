# django_ma/accounts/search_api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q, QuerySet

from partner.models import SubAdminTemp
from .models import CustomUser
from .utils import build_affiliation_display


RESULT_LIMIT = 50

SEARCH_FIELD_CANDIDATES: tuple[str, ...] = (
    "name",
    "regist",
    "channel",
    "division",
    "part",
    "branch",
)

# ✅ CustomUser에 실제로 있는 것만 (team_a/b/c, level은 SubAdminTemp에서 합칩니다)
RESPONSE_FIELD_CANDIDATES: tuple[str, ...] = (
    "id",
    "name",
    "regist",
    "channel",
    "division",
    "part",
    "branch",
    "enter",
    "quit",
    "grade",
    "status",
    "rank",
)


def _to_str(v) -> str:
    return str(v or "").strip()


def _existing_fields(model, candidates: Iterable[str]) -> list[str]:
    existing = {f.name for f in model._meta.get_fields()}
    return [f for f in candidates if f in existing]


def _is_text_like_field(model, field_name: str) -> bool:
    try:
        f = model._meta.get_field(field_name)
    except Exception:
        return False
    internal = getattr(f, "get_internal_type", lambda: "")()
    return internal in {"CharField", "TextField", "EmailField", "SlugField", "UUIDField"}


@dataclass(frozen=True)
class SearchParams:
    keyword: str
    scope: str
    requested_branch: str
    user_grade: str
    user_branch: str


def read_search_params(request) -> SearchParams:
    return SearchParams(
        keyword=_to_str(request.GET.get("q")),
        scope=_to_str(request.GET.get("scope")).lower(),
        requested_branch=_to_str(request.GET.get("branch")),
        user_grade=_to_str(getattr(request.user, "grade", "")),
        user_branch=_to_str(getattr(request.user, "branch", "")),
    )


def _apply_permission_scope(qs: QuerySet[CustomUser], *, user, p: SearchParams) -> QuerySet[CustomUser]:
    grade = p.user_grade

    if grade == "superuser":
        if p.scope == "branch" and p.requested_branch:
            return qs.filter(branch=p.requested_branch)
        return qs

    if grade == "head":
        return qs.filter(branch=p.user_branch)

    if grade == "leader":
        if p.scope == "branch":
            return qs.filter(branch=p.user_branch)

        sub_info = SubAdminTemp.objects.filter(user=user).first()
        if not sub_info:
            return qs.filter(branch=p.user_branch)

        level = _to_str(sub_info.level)
        team_a = _to_str(sub_info.team_a)
        team_b = _to_str(sub_info.team_b)
        team_c = _to_str(sub_info.team_c)

        # ✅ CustomUser ↔ SubAdminTemp(related_name=subadmin_detail) 기준 팀 제한
        if level == "A레벨" and team_a:
            return qs.filter(subadmin_detail__team_a=team_a)
        if level == "B레벨" and team_b:
            return qs.filter(subadmin_detail__team_b=team_b)
        if level == "C레벨" and team_c:
            return qs.filter(subadmin_detail__team_c=team_c)

        return qs.filter(branch=p.user_branch)

    if grade in {"basic", "inactive"}:
        return qs.filter(id=getattr(user, "id", None))

    return qs.none()


def _build_keyword_q(model, keyword: str) -> Q:
    keyword = _to_str(keyword)
    if not keyword:
        return Q()

    q = Q()
    for f in _existing_fields(model, SEARCH_FIELD_CANDIDATES):
        q |= Q(**{f"{f}__icontains": keyword})

    if "id" in _existing_fields(model, ("id",)) and _is_text_like_field(model, "id"):
        q |= Q(id__icontains=keyword)

    return q


def search_users_for_api(request) -> dict:
    """
    ✅ 단일 검색 API 구현 (SSOT)
    return: {"results": [ ... ]}
    - 핵심: SubAdminTemp(team/level)과 결합해서 affiliation_display를 만든다.
    """
    p = read_search_params(request)
    if not p.keyword:
        return {"results": []}

    qs = CustomUser.objects.all()
    qs = _apply_permission_scope(qs, user=request.user, p=p)

    kw_q = _build_keyword_q(CustomUser, p.keyword)
    if kw_q == Q():
        return {"results": []}

    # ✅ 응답에 넣을 CustomUser 필드만 안전 추출
    fields = _existing_fields(CustomUser, RESPONSE_FIELD_CANDIDATES)

    # 1) 먼저 CustomUser 결과를 뽑고 (values)
    users = list(
        qs.filter(kw_q)
        .order_by("name")
        .values(*fields)[:RESULT_LIMIT]
    )
    if not users:
        return {"results": []}

    # 2) 해당 user_id들에 대한 SubAdminTemp를 한 번에 조회해서 맵 구성
    ids = [u["id"] for u in users if u.get("id")]
    sa_map = {
        str(sa.user_id): {
            "level": _to_str(sa.level),
            "team_a": _to_str(sa.team_a),
            "team_b": _to_str(sa.team_b),
            "team_c": _to_str(sa.team_c),
            "position": _to_str(sa.position),
            "name": _to_str(sa.name),
        }
        for sa in SubAdminTemp.objects.filter(user_id__in=ids).only(
            "user_id", "level", "team_a", "team_b", "team_c", "position", "name"
        )
    }

    # 3) affiliation_display 생성(팀A+팀B+팀C 우선, 없으면 branch)
    results = []
    for u in users:
        sid = str(u.get("id") or "")
        sa = sa_map.get(sid, {})

        branch = _to_str(u.get("branch", ""))
        affiliation_display = build_affiliation_display(
            branch=branch,
            level=sa.get("level", ""),
            team_a=sa.get("team_a", ""),
            team_b=sa.get("team_b", ""),
            team_c=sa.get("team_c", ""),
        )

        results.append(
            {
                **u,
                # ✅ 프론트가 바로 쓸 수 있게 같이 내려줌
                "level": sa.get("level", ""),
                "team_a": sa.get("team_a", ""),
                "team_b": sa.get("team_b", ""),
                "team_c": sa.get("team_c", ""),
                "affiliation_display": affiliation_display,
            }
        )

    return {"results": results}
