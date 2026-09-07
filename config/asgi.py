"""
ASGI config for the To-Do app.

Application code (the `todos` package) lives under src/, not next to this
file - PYTHONPATH must include src/ when this module is loaded directly.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
