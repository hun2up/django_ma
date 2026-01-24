# django_ma/accounts/search_api.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q, QuerySet

from partner.models import SubAdminTemp
from .models import CustomUser


# =============================================================================
# Search Settings
# =============================================================================

RESULT_LIMIT = 50

# 검색에 사용할 후보 필드(모델에 실제 존재하는 것만 적용)
SEARCH_FIELD_CANDIDATES: tuple[str, ...] = (
    "name",
    "regist",
    "channel",
    "division",
    "part",
    "branch",
)

# 응답에 포함할 후보 필드(모델에 실제 존재하는 것만 적용)
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
    "rank",  # optional
)


# =============================================================================
# Small helpers
# =============================================================================

def _to_str(v) -> str:
    return str(v or "").strip()


def _existing_fields(model, candidates: Iterable[str]) -> list[str]:
    existing = {f.name for f in model._meta.get_fields()}
    return [f for f in candidates if f in existing]


def _is_text_like_field(model, field_name: str) -> bool:
    """
    id 같은 필드에 icontains를 걸 수 있는지(문자형 여부) 판단
    """
    try:
        f = model._meta.get_field(field_name)
    except Exception:
        return False

    internal = getattr(f, "get_internal_type", lambda: "")()
    return internal in {"CharField", "TextField", "EmailField", "SlugField", "UUIDField"}


# =============================================================================
# Request params normalization
# =============================================================================

@dataclass(frozen=True)
class SearchParams:
    keyword: str
    scope: str
    requested_branch: str
    user_grade: str
    user_branch: str


def read_search_params(request) -> SearchParams:
    """
    request에서 q/scope/branch 및 user grade/branch를 표준화해 추출
    """
    return SearchParams(
        keyword=_to_str(request.GET.get("q")),
        scope=_to_str(request.GET.get("scope")).lower(),
        requested_branch=_to_str(request.GET.get("branch")),
        user_grade=_to_str(getattr(request.user, "grade", "")),
        user_branch=_to_str(getattr(request.user, "branch", "")),
    )


# =============================================================================
# Permission / scope policy
# =============================================================================

def _apply_permission_scope(qs: QuerySet[CustomUser], *, user, p: SearchParams) -> QuerySet[CustomUser]:
    """
    통합 정책(기존 동작 + 요구 개선 반영):

    - superuser:
        * 전체 검색 허용
        * scope=branch AND branch 파라미터 있으면 해당 branch로 제한 가능
    - main_admin:
        * 무조건 본인 branch로 제한
    - sub_admin:
        * scope=branch면 "본인 branch 전체 검색" 허용 (요청하신 개선 포인트)
        * scope!=branch면 SubAdminTemp(level/team) 기준으로 팀 제한 (기존 유지)
          - 조건 불명확/정보 없음 → branch fallback
    - basic/inactive:
        * 본인만
    - 그 외:
        * 결과 없음
    """
    grade = p.user_grade

    if grade == "superuser":
        if p.scope == "branch" and p.requested_branch:
            return qs.filter(branch=p.requested_branch)
        return qs

    if grade == "main_admin":
        return qs.filter(branch=p.user_branch)

    if grade == "sub_admin":
        if p.scope == "branch":
            return qs.filter(branch=p.user_branch)

        sub_info = SubAdminTemp.objects.filter(user=user).first()
        if not sub_info:
            return qs.filter(branch=p.user_branch)

        level = _to_str(sub_info.level)
        team_a = _to_str(sub_info.team_a)
        team_b = _to_str(sub_info.team_b)
        team_c = _to_str(sub_info.team_c)

        # 기존 로직 유지: 레벨별 팀 단위 제한
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


# =============================================================================
# Keyword Q builder
# =============================================================================

def _build_keyword_q(model, keyword: str) -> Q:
    """
    모델에 존재하는 필드에만 icontains를 적용해 OR 조건 구성.
    """
    keyword = _to_str(keyword)
    if not keyword:
        return Q()

    q = Q()

    # 일반 후보 필드들
    for f in _existing_fields(model, SEARCH_FIELD_CANDIDATES):
        q |= Q(**{f"{f}__icontains": keyword})

    # id는 문자형일 때만
    if "id" in _existing_fields(model, ("id",)) and _is_text_like_field(model, "id"):
        q |= Q(id__icontains=keyword)

    return q


# =============================================================================
# Public function (single source of truth)
# =============================================================================

def search_users_for_api(request) -> dict:
    """
    ✅ 단일 검색 API 구현 (SSOT)
    return 형태: {"results": [ ... ]}
    """
    p = read_search_params(request)
    if not p.keyword:
        return {"results": []}

    qs = CustomUser.objects.all()
    qs = _apply_permission_scope(qs, user=request.user, p=p)

    kw_q = _build_keyword_q(CustomUser, p.keyword)
    if kw_q == Q():
        return {"results": []}

    # 응답 필드는 "있는 것만" 안전하게
    fields = _existing_fields(CustomUser, RESPONSE_FIELD_CANDIDATES)

    users = (
        qs.filter(kw_q)
        .order_by("name")
        .values(*fields)[:RESULT_LIMIT]
    )

    return {"results": list(users)}
