import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


def _csv_env(name: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, "").split(",") if v.strip()]


def _origin(url: str) -> str:
    return url.strip().rstrip("/")


def _host_from_url(url: str) -> str | None:
    if not url.strip():
        return None
    parsed = urlparse(url.strip())
    return parsed.hostname


VERCEL_URL = os.getenv("VERCEL_URL", "").strip()
VERCEL = os.getenv("VERCEL", "").lower() in ("1", "true", "yes")

_default_backend = (
    f"https://{VERCEL_URL}" if VERCEL_URL else "http://127.0.0.1:8000"
)
_default_frontend = (
    f"https://{VERCEL_URL}" if VERCEL_URL else "http://localhost:5173"
)

BACKEND_URL = _origin(os.getenv("BACKEND_URL", _default_backend))
FRONTEND_URL = _origin(os.getenv("FRONTEND_URL", _default_frontend))

SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv(
    "DJANGO_SECRET_KEY", "dev-only-change-in-production"
)
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

_allowed = _csv_env("ALLOWED_HOSTS")
if not _allowed:
    _allowed = ["localhost", "127.0.0.1"]
    backend_host = _host_from_url(BACKEND_URL)
    if backend_host and backend_host not in _allowed:
        _allowed.append(backend_host)
    if VERCEL or VERCEL_URL:
        for host in (".vercel.app",):
            if host not in _allowed:
                _allowed.append(host)
ALLOWED_HOSTS = _allowed

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "trips",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "spotter_api.urls"
WSGI_APPLICATION = "spotter_api.wsgi.application"

DATABASES = {}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"
USE_TZ = True

STATIC_URL = "static/"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}

_cors = _csv_env("CORS_ALLOWED_ORIGINS")
if not _cors:
    _cors = []
    if FRONTEND_URL:
        _cors.append(FRONTEND_URL)
    if DEBUG:
        for origin in (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ):
            if origin not in _cors:
                _cors.append(origin)
CORS_ALLOWED_ORIGINS = _cors
CORS_ALLOW_CREDENTIALS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
