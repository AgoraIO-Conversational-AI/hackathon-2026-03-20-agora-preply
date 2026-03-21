import os
import urllib.request

from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=503)


@ensure_csrf_cookie
def spa_view(request):
    return render(request, "spa.html")


def vite_proxy(request, path):
    """Proxy requests to Vite dev server for public assets."""
    vite_port = os.environ.get("FRONTEND_PORT", "3006")
    vite_url = f"http://localhost:{vite_port}/{path}"
    try:
        with urllib.request.urlopen(vite_url, timeout=5) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            return HttpResponse(content, content_type=content_type)
    except Exception:
        return HttpResponse(status=404)
