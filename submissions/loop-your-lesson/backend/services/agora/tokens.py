"""Agora RTC token generation.

Generates tokens for students to join voice practice channels.
The ConvoAI agent gets its own token via the start_agent API.

Requires: agora-token-builder package
"""

import logging
import time
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_SECONDS = 86400  # 24 hours

# Role constants
ROLE_PUBLISHER = 1
ROLE_SUBSCRIBER = 2


def generate_rtc_token(
    channel_name: str,
    uid: int,
) -> str:
    """Generate an RTC token for a student to join a voice practice channel."""
    from agora_token_builder import RtcTokenBuilder

    current_ts = int(time.time())
    privilege_expired_ts = current_ts + TOKEN_EXPIRY_SECONDS

    return RtcTokenBuilder.buildTokenWithUid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        ROLE_PUBLISHER,
        privilege_expired_ts,
    )


def generate_channel_name(student_id: str, lesson_id: str) -> str:
    """Unique channel name per voice practice session.

    Agora channels must be <= 64 bytes. We use short hashes of the IDs
    plus a random suffix to avoid 409 Conflict on re-join.
    """
    import hashlib

    lid = hashlib.sha256(lesson_id.encode()).hexdigest()[:8]
    sid = hashlib.sha256(student_id.encode()).hexdigest()[:8]
    suffix = uuid.uuid4().hex[:6]
    return f"vp_{lid}_{sid}_{suffix}"
