# django_ma/manual/utils/parsing.py

from __future__ import annotations

from typing import Any


def to_str(v: Any) -> str:
    """None/공백 입력을 안전하게 문자열로 정규화"""
    return str(v or "").strip()


def is_digits(v: Any) -> bool:
    """int로 변환 가능한 숫자 문자열인지 체크"""
    return str(v or "").isdigit()
