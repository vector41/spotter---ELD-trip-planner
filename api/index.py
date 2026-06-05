"""Vercel serverless entrypoint for the Django API."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotter_api.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
