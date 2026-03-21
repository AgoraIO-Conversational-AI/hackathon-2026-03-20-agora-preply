import os

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://dev:pass@localhost:5432/loop_dev",
    ),
}

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6381/0")

# Temporal
TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "localhost")
TEMPORAL_PORT = int(os.environ.get("TEMPORAL_PORT", "7235"))
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3006",
    "http://127.0.0.1:3006",
]
CORS_ALLOW_CREDENTIALS = True

# AI
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Classtime
CLASSTIME_TEACHER_TOKEN = os.environ.get("CLASSTIME_TEACHER_TOKEN", "")
CLASSTIME_ADMIN_TOKEN = os.environ.get("CLASSTIME_ADMIN_TOKEN", "")
CLASSTIME_ORG_ID = os.environ.get("CLASSTIME_ORG_ID", "")
CLASSTIME_SCHOOL_ID = os.environ.get("CLASSTIME_SCHOOL_ID", "")
CLASSTIME_FOLDER_ID = os.environ.get("CLASSTIME_FOLDER_ID", "")

# django-vite
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG,
        "dev_server_host": "localhost",
        "dev_server_port": int(os.environ.get("FRONTEND_PORT", "3006")),
        "manifest_path": BASE_DIR / "static" / "dist" / ".vite" / "manifest.json",  # noqa: F405
        "static_url_prefix": "/",
    },
}
