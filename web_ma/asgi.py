"""
ASGI config for web_ma project.
"""

# django_ma/web_ma/asgi.py

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_ma.settings")

application = get_asgi_application()
