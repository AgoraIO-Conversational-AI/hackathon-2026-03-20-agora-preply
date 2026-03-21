import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

CLASSTIME_REST_BASE = "https://api.classtime.com/teachers-api/v2"
CLASSTIME_PROTO_BASE = "https://www.classtime.com/service/public"


class ClasstimeError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response_body: dict | None = None):
        self.status_code = status_code
        self.response_body = response_body or {}
        super().__init__(message)


def _get_token() -> str:
    token = settings.CLASSTIME_TEACHER_TOKEN
    if not token:
        raise ClasstimeError("CLASSTIME_TEACHER_TOKEN not set")
    return token


# --- REST API client (question sets + questions) ---


def _rest_headers_for(token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://www.classtime.com",
        "Referer": "https://www.classtime.com/",
        "Cookie": f"service-jwt-0={token}",
    }


def _rest_headers() -> dict[str, str]:
    return _rest_headers_for(_get_token())


def rest_post(path: str, body: dict) -> dict:
    """POST to REST API. Returns parsed JSON response."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.post(url, json=body, headers=_rest_headers(), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        logger.error("Classtime REST %s %s: %s", resp.status_code, path, data)
        raise ClasstimeError(
            f"REST {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


def rest_patch(path: str, body: dict) -> dict:
    """PATCH to REST API. Returns parsed JSON response."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.patch(url, json=body, headers=_rest_headers(), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        logger.error("Classtime REST PATCH %s %s: %s", resp.status_code, path, data)
        raise ClasstimeError(
            f"REST PATCH {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


def rest_get(path: str) -> dict | list:
    """GET from REST API. Returns parsed JSON response."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.get(url, headers=_rest_headers(), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        raise ClasstimeError(
            f"REST GET {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


# --- Proto service API client (sessions + results) ---


def _proto_headers_for(token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json,*/*",
        "Authorization": f"JWT {token}",
    }


def _proto_headers() -> dict[str, str]:
    return _proto_headers_for(_get_token())


def proto_call(service: str, method: str, body: dict) -> dict:
    """Call Proto service API. Returns parsed JSON response."""
    url = f"{CLASSTIME_PROTO_BASE}/{service}/{method}"
    resp = httpx.post(url, json=body, headers=_proto_headers(), timeout=30)
    data = resp.json()
    if "classtimeErrorCode" in data and data.get("message"):
        logger.error("Classtime Proto %s/%s: %s", service, method, data["message"])
        raise ClasstimeError(
            f"Proto {service}/{method}: {data['message']}",
            response_body=data,
        )
    return data


# --- Per-token variants (for per-teacher/student operations) ---


def rest_post_as(token: str, path: str, body: dict) -> dict:
    """POST to REST API with an explicit token."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.post(url, json=body, headers=_rest_headers_for(token), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        logger.error("Classtime REST %s %s: %s", resp.status_code, path, data)
        raise ClasstimeError(
            f"REST {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


def rest_get_as(token: str, path: str) -> dict | list:
    """GET from REST API with an explicit token."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.get(url, headers=_rest_headers_for(token), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        raise ClasstimeError(
            f"REST GET {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


def rest_patch_as(token: str, path: str, body: dict) -> dict:
    """PATCH to REST API with an explicit token."""
    url = f"{CLASSTIME_REST_BASE}/{path}"
    resp = httpx.patch(url, json=body, headers=_rest_headers_for(token), timeout=30)
    if resp.status_code >= 400:
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text[:500]}
        logger.error("Classtime REST PATCH %s %s: %s", resp.status_code, path, data)
        raise ClasstimeError(
            f"REST PATCH {path} failed: {resp.status_code}",
            status_code=resp.status_code,
            response_body=data,
        )
    return resp.json()


def proto_call_as(token: str, service: str, method: str, body: dict) -> dict:
    """Call Proto service API with an explicit token."""
    url = f"{CLASSTIME_PROTO_BASE}/{service}/{method}"
    resp = httpx.post(url, json=body, headers=_proto_headers_for(token), timeout=30)
    data = resp.json()
    if "classtimeErrorCode" in data and data.get("message"):
        logger.error("Classtime Proto %s/%s: %s", service, method, data["message"])
        raise ClasstimeError(
            f"Proto {service}/{method}: {data['message']}",
            response_body=data,
        )
    return data
