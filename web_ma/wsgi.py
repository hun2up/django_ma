"""
WSGI config for web_ma project.
"""

# django_ma/web_ma/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web_ma.settings")

application = get_wsgi_application()
