# django_ma/board/templatetags/querystring.py
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """
    현재 request.GET을 복사해서 kwargs로 값 교체 후 querystring 반환.
    사용 예:
      {% qs_replace page=3 %}
      -> "search_type=title&keyword=abc&page=3" (앞에 ? 없음)

    값이 None/"" 이면 해당 키 제거.
    """
    request = context.get("request")
    if not request:
        return urlencode(kwargs, doseq=True)

    q = request.GET.copy()
    for k, v in kwargs.items():
        if v is None or v == "":
            q.pop(k, None)
        else:
            q[k] = str(v)

    return q.urlencode()
