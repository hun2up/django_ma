# django_ma/board/services/listing.py
# =========================================================
# Listing Services
# - 목록 공통 필터/검색/페이지네이션 (Post/Task 공용)
# - 기능 영향 최소화를 위해 기존 로직 1:1로 이동
# =========================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.dateparse import parse_date

from ..constants import PER_PAGE_CHOICES

User = get_user_model()


# ---------------------------------------------------------
# ✅ 공용 UI: 담당자 목록
# ---------------------------------------------------------
def get_handlers() -> List[str]:
    """담당자 목록: superuser의 name만 노출(기존 정책 유지)"""
    return list(
        User.objects
        .filter(grade="superuser")
        .exclude(name__isnull=True)
        .exclude(name__exact="")
        .values_list("name", flat=True)
        .distinct()
        .order_by("name")
    )


# ---------------------------------------------------------
# ✅ QueryString / Paging
# ---------------------------------------------------------
def get_per_page(request: HttpRequest, default: int = 10) -> int:
    raw = str(request.GET.get("per_page", "")).strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return n if n in PER_PAGE_CHOICES else default


def build_query_string_without_page(request: HttpRequest) -> str:
    q = request.GET.copy()
    q.pop("page", None)
    return q.urlencode()


def paginate(request: HttpRequest, qs: QuerySet, *, default_per_page: int = 10):
    per_page = get_per_page(request, default=default_per_page)
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    return page_obj, per_page


# ---------------------------------------------------------
# ✅ Date range
# ---------------------------------------------------------
def parse_date_range(request: HttpRequest) -> Tuple[str, str, Optional[Any], Optional[Any]]:
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    return date_from_raw, date_to_raw, date_from, date_to


# ---------------------------------------------------------
# ✅ 검색/필터
# ---------------------------------------------------------
def apply_keyword_filter(
    qs: QuerySet,
    keyword: str,
    search_type: str,
    *,
    title_field: str,
    content_field: str,
    user_name_field: str,
) -> QuerySet:
    """검색 타입(title/content/title_content/user_name)에 따른 keyword 필터"""
    if not keyword:
        return qs

    if search_type == "title":
        return qs.filter(**{f"{title_field}__icontains": keyword})
    if search_type == "content":
        return qs.filter(**{f"{content_field}__icontains": keyword})
    if search_type == "title_content":
        return qs.filter(
            Q(**{f"{title_field}__icontains": keyword}) |
            Q(**{f"{content_field}__icontains": keyword})
        )
    if search_type == "user_name":
        return qs.filter(**{f"{user_name_field}__icontains": keyword})

    # fallback
    return qs.filter(**{f"{title_field}__icontains": keyword})


def apply_common_list_filters(
    qs: QuerySet,
    *,
    date_from,
    date_to,
    selected_category: str,
    selected_handler: str,
    selected_status: str,
    category_field: str = "category",
    handler_field: str = "handler",
    status_field: str = "status",
    created_field: str = "created_at",
) -> QuerySet:
    """게시판 목록 공용 필터(기간/카테고리/담당자/상태)"""
    if date_from:
        qs = qs.filter(**{f"{created_field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{created_field}__date__lte": date_to})

    if selected_category and selected_category != "전체":
        qs = qs.filter(**{f"{category_field}__iexact": selected_category})

    if selected_handler != "전체":
        qs = qs.filter(**{handler_field: selected_handler})

    if selected_status != "전체":
        qs = qs.filter(**{status_field: selected_status})

    return qs


# ---------------------------------------------------------
# ✅ Request param bundle (SSOT)
# ---------------------------------------------------------
@dataclass(frozen=True)
class ListParams:
    keyword: str
    search_type: str
    selected_handler: str
    selected_status: str
    selected_category: str
    date_from_raw: str
    date_to_raw: str
    date_from: Optional[Any]
    date_to: Optional[Any]


def read_list_params(request: HttpRequest) -> ListParams:
    keyword = (request.GET.get("keyword") or "").strip()
    search_type = (request.GET.get("search_type") or "title").strip()

    selected_handler = (request.GET.get("handler") or "전체").strip()
    selected_status = (request.GET.get("status") or "전체").strip()
    selected_category = (request.GET.get("category") or "전체").strip()

    date_from_raw, date_to_raw, date_from, date_to = parse_date_range(request)

    return ListParams(
        keyword=keyword,
        search_type=search_type,
        selected_handler=selected_handler,
        selected_status=selected_status,
        selected_category=selected_category,
        date_from_raw=date_from_raw,
        date_to_raw=date_to_raw,
        date_from=date_from,
        date_to=date_to,
    )
