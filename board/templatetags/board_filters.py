# django_ma/board/templatetags/board_filters.py

import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    if value is None:
        return ""
    return os.path.basename(str(value))