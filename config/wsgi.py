"""
WSGI config for the To-Do app.

Application code (the `todos` package) lives under src/, not next to this
file - PYTHONPATH must include src/ when this module is loaded directly by
gunicorn (the Dockerfile sets this; manage.py does it itself for local runs).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
