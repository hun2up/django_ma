# django_ma/board/views/__init__.py
# =========================================================
# Public View API
# - urls.py가 기존처럼 "from board import views" 해도 동작하게
#   함수들을 re-export
# =========================================================

from .posts import *
from .tasks import *
from .forms import *
from .attachments import *
