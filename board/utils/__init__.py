# django_ma/board/utils/__init__.py

from .pdf_support_utils import generate_request_support
from .pdf_states_utils import generate_request_states

__all__ = [
    "generate_request_support",
    "generate_request_states",
]
