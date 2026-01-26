# django_ma/accounts/utils.py
from __future__ import annotations

def build_affiliation_display(*, branch="", level="", team_a="", team_b="", team_c="") -> str:
    """
    partner 쪽과 동일한 소속 표시 규칙
    """
    parts = []

    if branch:
        parts.append(branch)

    level = (level or "").strip()
    team_a = (team_a or "").strip()
    team_b = (team_b or "").strip()
    team_c = (team_c or "").strip()

    if level == "A레벨" and team_a:
        parts.append(team_a)
    elif level == "B레벨" and team_b:
        parts.append(team_b)
    elif level == "C레벨" and team_c:
        parts.append(team_c)

    return " > ".join(parts)
