"""Session store for voice practice sessions.

Primary: Redis with 2-hour TTL.
Fallback: In-memory dict if Redis is unavailable (hackathon safety net).
"""

import json
import logging

import redis.asyncio as aioredis
from django.conf import settings

from services.convoai.schemas import MasteryState

logger = logging.getLogger(__name__)

SESSION_TTL = 7200  # 2 hours

# Key prefixes
SESSION_KEY = "voice:session:{session_id}"
CLASSTIME_INDEX_KEY = "voice:classtime:{code}"

# Lazy singleton Redis connection
_redis: aioredis.Redis | None = None
_redis_available: bool | None = None  # None = untested

# In-memory fallback (used when Redis is down)
_fallback: dict[str, str] = {}
_fallback_index: dict[str, set[str]] = {}


def _get_redis() -> aioredis.Redis:
    """Get the shared async Redis client."""
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis


async def _use_redis() -> bool:
    """Check if Redis is reachable (cached after first check)."""
    global _redis_available  # noqa: PLW0603
    if _redis_available is not None:
        return _redis_available
    try:
        r = _get_redis()
        await r.ping()
        _redis_available = True
        logger.info("Redis connected for session store")
    except Exception:
        logger.warning("Redis unavailable, falling back to in-memory session store")
        _redis_available = False
    return _redis_available


async def save_session(
    session_id: str,
    *,
    agent_id: str,
    channel: str,
    student_id: str,
    lesson_id: str,
    classtime_session_code: str | None,
    mastery: MasteryState,
    context_args: dict,
) -> None:
    """Save a voice session.

    Args:
        context_args: Constructor args for VoicePracticeContext (serializable).
            VoicePracticeContext itself has methods, so we store its args
            and reconstruct on read.
    """
    data = {
        "agent_id": agent_id,
        "channel": channel,
        "student_id": student_id,
        "lesson_id": lesson_id,
        "classtime_session_code": classtime_session_code,
        "mastery": mastery.model_dump(),
        "context_args": context_args,
        "agent_alive": True,
    }
    serialized = json.dumps(data)

    if await _use_redis():
        r = _get_redis()
        key = SESSION_KEY.format(session_id=session_id)
        await r.set(key, serialized, ex=SESSION_TTL)
        if classtime_session_code:
            index_key = CLASSTIME_INDEX_KEY.format(code=classtime_session_code)
            await r.sadd(index_key, session_id)
            await r.expire(index_key, SESSION_TTL)
    else:
        _fallback[session_id] = serialized
        if classtime_session_code:
            _fallback_index.setdefault(classtime_session_code, set()).add(session_id)

    logger.debug("Saved session %s", session_id)


async def get_session(session_id: str) -> dict | None:
    """Get session data by session_id. Returns None if not found."""
    if await _use_redis():
        r = _get_redis()
        key = SESSION_KEY.format(session_id=session_id)
        raw = await r.get(key)
    else:
        raw = _fallback.get(session_id)

    if raw is None:
        return None
    data = json.loads(raw)
    data["mastery"] = MasteryState.model_validate(data["mastery"])
    return data


async def update_mastery(session_id: str, mastery: MasteryState) -> None:
    """Update the mastery state for a session."""
    session = await get_session(session_id)
    if session is None:
        logger.warning("Cannot update mastery: session %s not found", session_id)
        return

    session["mastery"] = mastery.model_dump()
    serialized = json.dumps(session)

    if await _use_redis():
        r = _get_redis()
        key = SESSION_KEY.format(session_id=session_id)
        ttl = await r.ttl(key)
        await r.set(key, serialized, ex=max(ttl, 60))
    else:
        _fallback[session_id] = serialized


async def mark_agent_dead(session_id: str) -> None:
    """Mark agent as dead (ConvoAI returned error on /update or /speak)."""
    session = await get_session(session_id)
    if session is None:
        return
    session["agent_alive"] = False
    if isinstance(session["mastery"], MasteryState):
        session["mastery"] = session["mastery"].model_dump()
    serialized = json.dumps(session)

    if await _use_redis():
        r = _get_redis()
        key = SESSION_KEY.format(session_id=session_id)
        ttl = await r.ttl(key)
        await r.set(key, serialized, ex=max(ttl, 60))
    else:
        _fallback[session_id] = serialized
    logger.warning("Marked agent dead for session %s", session_id)


async def delete_session(session_id: str) -> dict | None:
    """Delete session and return its data (for cleanup). Returns None if not found."""
    session = await get_session(session_id)
    if session is None:
        return None

    if await _use_redis():
        r = _get_redis()
        key = SESSION_KEY.format(session_id=session_id)
        await r.delete(key)
        code = session.get("classtime_session_code")
        if code:
            index_key = CLASSTIME_INDEX_KEY.format(code=code)
            await r.srem(index_key, session_id)
    else:
        _fallback.pop(session_id, None)
        code = session.get("classtime_session_code")
        if code and code in _fallback_index:
            _fallback_index[code].discard(session_id)

    logger.debug("Deleted session %s", session_id)
    return session


async def get_sessions_by_classtime_code(code: str) -> list[tuple[str, dict]]:
    """Find all voice sessions linked to a Classtime session code."""
    if await _use_redis():
        r = _get_redis()
        index_key = CLASSTIME_INDEX_KEY.format(code=code)
        session_ids = await r.smembers(index_key)
    else:
        session_ids = _fallback_index.get(code, set())

    results = []
    for sid in session_ids:
        session = await get_session(sid)
        if session:
            results.append((sid, session))
    return results
