# partner/views/utils.py
# ------------------------------------------------------------
# ✅ 공용 유틸(날짜/파싱/권한 스코프/소속 표기/요율 테이블 검색 등)
# ------------------------------------------------------------

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q
from django.utils import timezone

from accounts.models import CustomUser
from partner.models import SubAdminTemp, TableSetting
from .constants import BRANCH_PARTS


# ------------------------------------------------------------
# 날짜/월도 유틸
# ------------------------------------------------------------
def get_now_ym() -> Tuple[int, int]:
    now = timezone.localtime(timezone.now())
    return now.year, now.month


def normalize_month(month: str) -> str:
    month = (month or "").strip()
    if not month:
        return ""
    if "-" in month:
        try:
            y, m = month.split("-")
            return f"{y}-{int(m):02d}"
        except Exception:
            return month
    digits = "".join([c for c in month if c.isdigit()])
    if len(digits) == 6:
        return f"{digits[:4]}-{digits[4:6]}"
    return month


def parse_yyyy_mm_dd_or_none(value: str):
    v = (value or "").strip()
    if not v:
        return None
    return datetime.strptime(v, "%Y-%m-%d").date()


# ------------------------------------------------------------
# 현재 사용자 payload (JS boot에 주입)
# ------------------------------------------------------------
def build_current_user_payload(user: CustomUser) -> Dict[str, Any]:
    return {
        "grade": getattr(user, "grade", "") or "",
        "branch": getattr(user, "branch", "") or "",
        "part": getattr(user, "part", "") or "",
        "id": getattr(user, "id", "") or "",
        "name": getattr(user, "name", "") or "",
    }


# ------------------------------------------------------------
# Branch/Part 스코프 해석
# ------------------------------------------------------------
def resolve_branch_for_query(user: CustomUser, branch_param: str) -> str:
    """GET 조회 스코프: superuser는 branch 파라미터를 존중, 그 외는 자기 지점 강제"""
    branch_param = (branch_param or "").strip()
    if getattr(user, "grade", "") == "superuser":
        return branch_param
    return (getattr(user, "branch", "") or "").strip()


def resolve_branch_for_write(user: CustomUser, branch_payload: str) -> str:
    """쓰기 스코프: superuser는 payload branch 사용, 그 외는 자기 지점 우선"""
    branch_payload = (branch_payload or "").strip()
    if getattr(user, "grade", "") == "superuser":
        return branch_payload or "-"
    return (getattr(user, "branch", "") or branch_payload or "-").strip()


def resolve_part_for_write(user: CustomUser, part_payload: str) -> str:
    part_payload = (part_payload or "").strip()
    return part_payload or (getattr(user, "part", "") or "-").strip()


# ------------------------------------------------------------
# 소속 표기
# ------------------------------------------------------------
def _clean_dash(v: str) -> str:
    v = (v or "").strip()
    return "" if v == "-" else v


def build_affiliation_display(user: CustomUser) -> str:
    """
    ✅ 기존 소속 표기(팀A/B/C 중 유효값만 노출)
    - 팀A가 없으면 branch만
    - 팀A/B/C 있으면 "team_a team_b team_c"
    """
    branch = _clean_dash(getattr(user, "branch", "")) or "-"
    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return branch

    team_a = _clean_dash(getattr(sa, "team_a", ""))
    team_b = _clean_dash(getattr(sa, "team_b", ""))
    team_c = _clean_dash(getattr(sa, "team_c", ""))

    if not team_a:
        return branch

    parts = [p for p in [team_a, team_b, team_c] if p]
    return " ".join(parts) if parts else branch


def build_requester_affiliation_chain(user: CustomUser) -> str:
    """
    ✅ 요청자 소속 표기(지점 + 팀A + 팀B + 팀C)
    - 팀A 없으면 지점까지만
    - "-" / 빈값은 제외
    """
    def _clean(v: str) -> str:
        v = (v or "").strip()
        return "" if (not v or v == "-") else v

    branch = _clean(getattr(user, "branch", "")) or "-"
    parts = [branch]

    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return " ".join([p for p in parts if p])

    team_a = _clean(getattr(sa, "team_a", ""))
    team_b = _clean(getattr(sa, "team_b", ""))
    team_c = _clean(getattr(sa, "team_c", ""))

    if team_a:
        parts.append(team_a)
    if team_b:
        parts.append(team_b)
    if team_c:
        parts.append(team_c)

    return " ".join([p for p in parts if p])


# ------------------------------------------------------------
# leader 레벨별 팀 필터: requester_id 허용 목록
# ------------------------------------------------------------
def get_level_team_filter_user_ids(user: CustomUser) -> List[str]:
    """
    ✅ leader 레벨별 팀 필터에 해당하는 '작성자(requester)' user_id 목록 반환
    - A레벨: team_a 동일
    - B레벨: team_b 동일
    - C레벨: team_c 동일
    - 레벨/팀값 없으면 빈 리스트
    """
    sa = SubAdminTemp.objects.filter(user=user).first()
    if not sa:
        return []

    level = (sa.level or "").strip()
    if level not in ["A레벨", "B레벨", "C레벨"]:
        return []

    field = {"A레벨": "team_a", "B레벨": "team_b", "C레벨": "team_c"}[level]
    my_team_value = _clean_dash(getattr(sa, field, "") or "")
    if not my_team_value:
        return []

    return list(
        SubAdminTemp.objects.filter(
            branch=(user.branch or "").strip(),
            **{f"{field}__iexact": my_team_value},
        ).values_list("user_id", flat=True)
    )


# ------------------------------------------------------------
# 테이블 요율 검색
# ------------------------------------------------------------
def find_table_rate(branch: str, table_name: str) -> str:
    table_name = (table_name or "").strip()
    if not table_name:
        return ""
    ts = TableSetting.objects.filter(branch=branch, table_name=table_name).order_by("order").first()
    return (ts.rate or "") if ts else ""


def find_part_by_branch(branch: str) -> str:
    """지점명으로 부서를 추정(우선 DB, fallback BRANCH_PARTS)"""
    b = (branch or "").strip()
    if not b:
        return ""

    p = (
        CustomUser.objects.filter(branch__iexact=b)
        .exclude(part__isnull=True)
        .exclude(part__exact="")
        .values_list("part", flat=True)
        .first()
    )
    if p:
        return str(p).strip()

    for part, branches in BRANCH_PARTS.items():
        if b in (branches or []):
            return part
    return ""
