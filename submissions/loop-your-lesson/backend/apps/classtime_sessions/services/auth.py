"""Classtime account provisioning and per-user token lifecycle.

Flow (verified against live API):
  1. Account/getOrCreateAccount  → classtime_account_id (idempotent)
  2. Account/associateMember     → add teacher to Preply org (teachers only)
  3. Account/createToken         → 7-day JWT for that user

Uses the SchoolAdmin token (CLASSTIME_ADMIN_TOKEN) for all admin operations.
Per-user tokens are cached on the Teacher/Student model.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from django.conf import settings

from apps.accounts.models import Student, Teacher

from .client import CLASSTIME_PROTO_BASE, ClasstimeError

logger = logging.getLogger(__name__)


def _admin_proto_call(service: str, method: str, body: dict) -> dict:
    """Proto API call using the SchoolAdmin token."""
    token = settings.CLASSTIME_ADMIN_TOKEN
    if not token:
        raise ClasstimeError("CLASSTIME_ADMIN_TOKEN not set")
    url = f"{CLASSTIME_PROTO_BASE}/{service}/{method}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json,*/*",
        "Authorization": f"JWT {token}",
    }
    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    data = resp.json()
    if "classtimeErrorCode" in data and data.get("message"):
        logger.error("Classtime admin %s/%s: %s", service, method, data["message"])
        raise ClasstimeError(
            f"Admin {service}/{method}: {data['message']}",
            response_body=data,
        )
    return data


# --- Account provisioning ---


def provision_teacher(
    subject: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """Create or retrieve a teacher account and associate with Preply org.

    Returns classtime_account_id. Idempotent (same subject = same account).
    """
    account_id = _create_account("TEACHER", subject, email, first_name, last_name)
    _associate_with_org(account_id)
    return account_id


def provision_student(
    subject: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """Create or retrieve a student account. No org association needed.

    Returns classtime_account_id. Idempotent (same subject = same account).
    """
    return _create_account("STUDENT", subject, email, first_name, last_name)


def _create_account(
    role: str,
    subject: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """Call Account/getOrCreateAccount. Returns accountId."""
    resp = _admin_proto_call(
        "Account",
        "getOrCreateAccount",
        {
            "role": role,
            "user_profile": {"first_name": first_name, "last_name": last_name},
            "subject": subject,
            "email": email,
        },
    )
    account_id = resp.get("accountId") or resp.get("account_id")
    if not account_id:
        raise ClasstimeError(
            f"getOrCreateAccount returned no account_id: {resp}",
            response_body=resp,
        )
    logger.info("Classtime account %s for %s (%s)", account_id, subject, role)
    return account_id


def _associate_with_org(account_id: str) -> None:
    """Call Account/associateMember to add account to Preply org."""
    org_id = getattr(settings, "CLASSTIME_ORG_ID", "")
    if not org_id:
        raise ClasstimeError("CLASSTIME_ORG_ID not set")
    _admin_proto_call(
        "Account",
        "associateMember",
        {
            "organization_id": org_id,
            "account_id": account_id,
        },
    )
    logger.info("Associated %s with org %s", account_id, org_id)


# --- Token lifecycle ---


def create_user_token(classtime_id: str) -> tuple[str, datetime]:
    """Mint a JWT for a Classtime account. Returns (token, expires_at)."""
    resp = _admin_proto_call(
        "Account",
        "createToken",
        {
            "classtime_id": classtime_id,
        },
    )
    token = resp.get("token")
    if not token:
        raise ClasstimeError(
            f"createToken returned no token: {resp}",
            response_body=resp,
        )
    valid_until = resp.get("validUntil") or resp.get("valid_until", "")
    expires_at = _parse_timestamp(valid_until)
    logger.info("Minted token for %s (expires %s)", classtime_id, expires_at)
    return token, expires_at


def _parse_timestamp(ts: str) -> datetime:
    """Parse Classtime timestamp like '2026-03-24T20:36:19.798077727Z'."""
    # Truncate nanoseconds to microseconds for Python's fromisoformat
    clean = ts.replace("Z", "+00:00")
    # Handle nanosecond precision (> 6 decimal places)
    if "." in clean:
        parts = clean.split(".")
        frac_and_tz = parts[1]
        # Split fraction from timezone
        for i, c in enumerate(frac_and_tz):
            if c in ("+", "-"):
                frac = frac_and_tz[:i][:6]  # truncate to microseconds
                tz = frac_and_tz[i:]
                clean = f"{parts[0]}.{frac}{tz}"
                break
    return datetime.fromisoformat(clean)


# --- High-level: ensure valid token ---


_TOKEN_REFRESH_BUFFER = timedelta(hours=1)


def ensure_teacher_token(teacher: Teacher) -> str:
    """Get a valid Classtime JWT for this teacher, provisioning if needed."""
    if not teacher.classtime_account_id:
        subject = f"preply-teacher-{teacher.preply_user_id or teacher.pk}"
        account_id = provision_teacher(subject, teacher.email, *_split_name(teacher.name))
        teacher.classtime_account_id = account_id
        teacher.save(update_fields=["classtime_account_id"])

    if (
        teacher.classtime_token
        and teacher.classtime_token_expires_at
        and teacher.classtime_token_expires_at > datetime.now(UTC) + _TOKEN_REFRESH_BUFFER
    ):
        return teacher.classtime_token

    token, expires_at = create_user_token(teacher.classtime_account_id)
    teacher.classtime_token = token
    teacher.classtime_token_expires_at = expires_at
    teacher.save(update_fields=["classtime_token", "classtime_token_expires_at"])
    return token


def ensure_student_token(student: Student) -> str:
    """Get a valid Classtime JWT for this student, provisioning if needed."""
    if not student.classtime_account_id:
        subject = f"preply-student-{student.preply_user_id or student.pk}"
        account_id = provision_student(subject, student.email, *_split_name(student.name))
        student.classtime_account_id = account_id
        student.save(update_fields=["classtime_account_id"])

    if (
        student.classtime_token
        and student.classtime_token_expires_at
        and student.classtime_token_expires_at > datetime.now(UTC) + _TOKEN_REFRESH_BUFFER
    ):
        return student.classtime_token

    token, expires_at = create_user_token(student.classtime_account_id)
    student.classtime_token = token
    student.classtime_token_expires_at = expires_at
    student.save(update_fields=["classtime_token", "classtime_token_expires_at"])
    return token


def _split_name(name: str) -> tuple[str, str]:
    """Split 'First Last' into (first, last). Handles single names."""
    parts = name.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0] if parts else "User", ""
