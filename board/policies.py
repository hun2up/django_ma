# django_ma/board/policies.py
# =========================================================
# Board Permission Policies (SSOT)
# - Post 조회/수정/삭제/첨부 다운로드 정책
# - 뷰는 "정책 호출"만 하도록 분리 (가독성/안전성 향상)
# =========================================================

from __future__ import annotations

from .constants import INACTIVE_GRADE


def norm_branch(s: str) -> str:
    """지점 표기 차(공백 등) 방어용 normalize."""
    return (s or "").strip()


def is_inactive(user) -> bool:
    """inactive 유저 여부"""
    return (getattr(user, "grade", "") or "") == INACTIVE_GRADE


def is_post_author(user, post) -> bool:
    """Post 작성자 여부 (user.id vs post.user_id string 비교 방어)"""
    # 사번 필드가 있으면(예: emp_id) 그 값을 우선 사용
    user_key = getattr(user, "emp_id", None) or getattr(user, "user_id", None) or getattr(user, "id", "")
    return str(user_key) == str(getattr(post, "user_id", ""))


def can_view_post(user, post) -> bool:
    """
    ✅ Post Visibility (중요 정책)
    - superuser: 전체
    - 작성자: 본인 글
    - head: 본인 글 + 본인 지점 글(user_branch 동일)
    - leader: 본인 글만
    """
    grade = getattr(user, "grade", "") or ""
    if grade == "superuser":
        return True
    if is_post_author(user, post):
        return True
    if grade == "head":
        return norm_branch(getattr(user, "branch", "")) == norm_branch(getattr(post, "user_branch", ""))
    return False


def can_edit_post(user, post) -> bool:
    """
    ✅ Post Edit/Delete 정책
    - superuser + 작성자
    """
    if (getattr(user, "grade", "") or "") == "superuser":
        return True
    return is_post_author(user, post)
