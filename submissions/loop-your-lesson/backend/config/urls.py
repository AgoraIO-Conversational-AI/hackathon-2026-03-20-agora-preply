from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from .views import health_check, spa_view, vite_proxy

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/v1/", include("config.api_urls")),
]

# Proxy public assets to Vite dev server in development
if settings.DEBUG:
    urlpatterns += [
        re_path(r"^(?P<path>assets/.*)$", vite_proxy),
        re_path(r"^(?P<path>loop/.*)$", vite_proxy),
    ]

# SPA catch-all (must be last)
urlpatterns += [
    re_path(r"^.*$", spa_view, name="spa"),
]
