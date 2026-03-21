import os

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DATABASE_HOST"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "NAME": os.environ.get("DATABASE_NAME"),
        "USER": os.environ.get("DATABASE_USERNAME"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD"),
    },
}

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "")

# Temporal (Temporal Cloud)
TEMPORAL_HOST = os.environ.get("TEMPORAL_HOST", "")
TEMPORAL_PORT = int(os.environ.get("TEMPORAL_PORT", "7233"))
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")
TEMPORAL_API_KEY = os.environ.get("TEMPORAL_API_KEY", "")

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# AI
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Classtime
CLASSTIME_TEACHER_TOKEN = os.environ.get("CLASSTIME_TEACHER_TOKEN", "")
CLASSTIME_FOLDER_ID = os.environ.get("CLASSTIME_FOLDER_ID", "")
CLASSTIME_ADMIN_TOKEN = os.environ.get("CLASSTIME_ADMIN_TOKEN", "")
CLASSTIME_SCHOOL_ID = os.environ.get("CLASSTIME_SCHOOL_ID", "")
CLASSTIME_ORG_ID = os.environ.get("CLASSTIME_ORG_ID", "")

# Static files (WhiteNoise serves them from gunicorn)
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
STATIC_URL = "/static/"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# WhiteNoise middleware
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# Serve Vite public assets (favicon, logo) at root URL (without /static/ prefix)
WHITENOISE_ROOT = BASE_DIR / "static" / "dist"  # noqa: F405

# django-vite (production mode, serve from built manifest)
DJANGO_VITE = {
    "default": {
        "dev_mode": False,
        "manifest_path": BASE_DIR / "static" / "dist" / ".vite" / "manifest.json",  # noqa: F405
        "static_url_prefix": "/",
    },
}

# Security
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]
