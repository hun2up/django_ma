# django_ma/accounts/views.py

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.urls import reverse

from accounts.models import CustomUser


@login_required
def upload_progress_view(request: HttpRequest) -> JsonResponse:
    task_id = (request.GET.get("task_id") or "").strip()
    if not task_id:
        return JsonResponse({"percent": 0, "status": "PENDING", "error": "", "download_url": ""})

    percent = cache.get(f"upload_progress:{task_id}", 0)
    status = cache.get(f"upload_status:{task_id}", "PENDING")
    error = cache.get(f"upload_error:{task_id}", "")

    download_url = ""
    if status == "SUCCESS":
        try:
            download_url = reverse("admin:upload_users_result", args=[task_id])
        except Exception:
            download_url = ""

    return JsonResponse({
        "percent": int(percent or 0),
        "status": status or "PENDING",
        "error": error or "",
        "download_url": download_url,
    })


class SessionCloseLoginView(LoginView):
    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        self.request.session.set_expiry(0)
        return response


# -------------------------
# Search helpers
# -------------------------
def _to_str(v) -> str:
    return str(v or "").strip()


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def _is_text_field(model, name: str) -> bool:
    """
    id가 AutoField(정수 PK)면 icontains 불가 -> False
    CharField/TextField류면 True
    """
    try:
        f = model._meta.get_field(name)
    except Exception:
        return False

    internal = getattr(f, "get_internal_type", lambda: "")()
    return internal in ("CharField", "TextField", "EmailField", "SlugField", "UUIDField")


@dataclass(frozen=True)
class SearchParams:
    keyword: str
    scope: str
    branch: str
    grade: str


def _read_search_params(request: HttpRequest) -> SearchParams:
    keyword = _to_str(request.GET.get("q"))
    scope = _to_str(request.GET.get("scope"))
    grade = _to_str(getattr(request.user, "grade", ""))

    user_branch = _to_str(getattr(request.user, "branch", ""))
    branch_param = _to_str(request.GET.get("branch"))

    # ✅ superuser만 branch 파라미터 허용 / 나머지는 본인 지점 고정
    if scope == "branch":
        branch = (branch_param or user_branch) if grade == "superuser" else user_branch
    else:
        branch = ""

    return SearchParams(keyword=keyword, scope=scope, branch=branch, grade=grade)


def _build_keyword_q(keyword: str) -> Q:
    """
    존재하는 필드만 대상으로 Q를 구성 (없거나 타입 안 맞으면 제외)
    """
    q = Q()

    # name
    if _has_field(CustomUser, "name"):
        q |= Q(name__icontains=keyword)

    # regist (사번)
    if _has_field(CustomUser, "regist"):
        q |= Q(regist__icontains=keyword)

    for f in ("channel", "division", "part", "branch"):
        if _has_field(CustomUser, f):
            q |= Q(**{f"{f}__icontains": keyword})

    # id는 "문자형일 때만" icontains 적용
    if _has_field(CustomUser, "id") and _is_text_field(CustomUser, "id"):
        q |= Q(id__icontains=keyword)

    return q


@login_required
def api_search_user(request: HttpRequest) -> JsonResponse:
    """
    /api/accounts/search-user/?q=...&scope=branch[&branch=...]
    """
    p = _read_search_params(request)
    if not p.keyword:
        return JsonResponse({"results": []})

    qs = CustomUser.objects.all()

    # scope=branch면 해당 지점 전체로 제한
    if p.scope == "branch":
        if not p.branch:
            return JsonResponse({"results": []})
        qs = qs.filter(branch=p.branch)

    kw_q = _build_keyword_q(p.keyword)
    if kw_q == Q():  # 검색 가능한 필드가 하나도 없으면 빈 결과
        return JsonResponse({"results": []})

    qs = qs.filter(kw_q).order_by("name")

    # ✅ values 필드도 "있는 것만" 선택
    fields = ["id", "name", "regist", "channel", "division", "part", "branch", "enter", "quit"]
    for opt in ("rank",):
        if _has_field(CustomUser, opt):
            fields.append(opt)

    users = qs.values(*fields)[:20]
    return JsonResponse({"results": list(users)})


# ✅ 호환용 alias (기존 /search-user/가 필요하면 동일 동작)
@login_required
def search_user(request: HttpRequest) -> JsonResponse:
    return api_search_user(request)