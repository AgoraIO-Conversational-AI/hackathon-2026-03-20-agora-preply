"""Classtime session lifecycle.

Solo sessions (recommended): /code/ URL, clean "Start" button.
Regular sessions: /student/login/ URL, full settings control.
"""

from __future__ import annotations

import logging

from apps.accounts.models import Student, Teacher
from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant
from apps.lessons.models import Lesson

from .auth import ensure_teacher_token
from .client import proto_call, proto_call_as, rest_patch, rest_patch_as
from .questions import create_question, create_question_set
from .schemas import (
    BooleanPayload,
    CategorizerItem,
    CategorizerPayload,
    FeedbackMode,
    Gap,
    GapChoice,
    GapPayload,
    MultipleChoicePayload,
    QuestionPayload,
    SingleChoiceOption,
    SingleChoicePayload,
    SorterPayload,
    build_session_settings,
)

logger = logging.getLogger(__name__)

STUDENT_URL_BASE = "https://www.classtime.com/student/login"
SOLO_URL_BASE = "https://www.classtime.com/code"

# Session status
STATUS_CREATED = "created"

# Payload type constants (from skill output)
PAYLOAD_BOOLEAN = "boolean"
PAYLOAD_CHOICE = "choice"
PAYLOAD_MULTIPLE_CHOICE = "multiple_choice"
PAYLOAD_GAP = "gap"
PAYLOAD_SORTER = "sorter"
PAYLOAD_CATEGORIZER = "categorizer"


def create_practice_session(
    question_set_id: str,
    title: str,
    feedback_mode: FeedbackMode = "practice",
    shuffle_questions: bool = False,
    tts_language: str | None = None,
    selected_question_ids: list[str] | None = None,
    token: str | None = None,
) -> str:
    """Create a practice session from a question set. Returns session_code."""
    settings = build_session_settings(
        title=title,
        feedback_mode=feedback_mode,
        shuffle_questions=shuffle_questions,
        tts_language=tts_language,
    )
    call = proto_call_as if token else proto_call
    args = (token, "Session", "createSession") if token else ("Session", "createSession")
    resp = call(
        *args,
        {
            "playlist": [
                {
                    "questionSetId": question_set_id,
                    "selectedQuestionIds": selected_question_ids or [],
                }
            ],
            "settings": settings,
        },
    )
    code = resp["session"]["code"]
    total = resp["session"].get("totalPoints", {}).get("pointsCentis", 0)
    n_questions = len(resp["session"]["settings"].get("activeQuestions", []))
    logger.info(
        "Created session %s (%d questions, %d centis): %s",
        code,
        n_questions,
        total,
        title,
    )
    return code


def get_session_details(session_code: str) -> dict:
    """Get full session with questions map and settings."""
    return proto_call("Session", "getSessionDetails", {"code": session_code})


def list_sessions() -> list[dict]:
    """List all teacher's sessions."""
    resp = proto_call("Session", "getSessions", {})
    return resp.get("sessions", [])


def check_session_health(session_code: str) -> dict:
    """Check if a session is ready for students."""
    return proto_call("Session", "checkSessionHealth", {"code": session_code})


def end_session(session_code: str) -> None:
    """End a session (students can no longer answer)."""
    proto_call(
        "Session",
        "changeSessionState",
        {
            "sessionCode": session_code,
            "state": "ENDED",
        },
    )
    logger.info("Ended session %s", session_code)


def archive_session(session_code: str) -> None:
    """Archive a session (read-only)."""
    proto_call(
        "Session",
        "changeSessionState",
        {
            "sessionCode": session_code,
            "state": "ARCHIVED",
        },
    )


def get_student_url(session_code: str) -> str:
    """Build the student-facing URL for a regular session."""
    return f"{STUDENT_URL_BASE}/{session_code}"


# --- Solo session (clean /code/ URL) ---


def enable_solo(question_set_id: str, token: str | None = None) -> str:
    """Enable anonymous solo access on a question set. Returns the secretLink.

    This PATCHes the QS to set anonymousSoloSessionRef = "create",
    which unlocks the Session/soloSession API for this QS.
    """
    path = f"question-sets/{question_set_id}/"
    body = {"anonymousSoloSessionRef": "create"}
    resp = rest_patch_as(token, path, body) if token else rest_patch(path, body)
    secret = resp["secretLink"]
    logger.info("Enabled solo for QS %s (secret: %s)", question_set_id, secret)
    return secret


def create_solo_session(
    secret_link: str,
    owner_account_id: str | None = None,
    token: str | None = None,
) -> str:
    """Create a solo session from a QS secretLink. Returns the /code/ URL.

    The QS must have anonymousSoloSessionRef enabled first (see enable_solo).
    Each call creates a NEW session (not idempotent).
    Student URL: https://www.classtime.com/code/{CODE}
    """
    body: dict = {
        "secretLink": secret_link,
        "isAnonymous": True,
    }
    if owner_account_id:
        body["ownerAccountId"] = owner_account_id
    call = proto_call_as if token else proto_call
    args = (token, "Session", "soloSession") if token else ("Session", "soloSession")
    resp = call(*args, body)
    url = resp["redirectUrl"]
    code = url.split("/")[-1]
    logger.info("Created solo session %s from secret %s", code, secret_link)
    return url


def create_solo_practice(
    question_set_id: str,
    owner_account_id: str | None = None,
    token: str | None = None,
) -> str:
    """Full flow: enable solo + create solo session. Returns /code/ URL.

    This is the simplest way to get a student-facing URL from a question set.
    Student sees a clean "Start" button, no login required.
    """
    secret = enable_solo(question_set_id, token=token)
    return create_solo_session(secret, owner_account_id=owner_account_id, token=token)


def get_solo_url(code: str) -> str:
    """Build the student-facing URL for a solo session."""
    return f"{SOLO_URL_BASE}/{code}"


def set_session_settings(
    session_code: str,
    settings: dict,
    active_questions: list[dict] | None = None,
    token: str | None = None,
) -> None:
    """Apply settings to an existing session.

    Solo sessions are created with Classtime defaults. Call this after
    create_solo_session() to apply our feedback/reflection/grading settings.

    IMPORTANT: Include activeQuestions from getSessionDetails or Classtime
    will deactivate all questions (student sees "waiting for questions").
    """
    if active_questions:
        settings["activeQuestions"] = active_questions
    call = proto_call_as if token else proto_call
    args = (token, "Session", "setSessionSettings") if token else ("Session", "setSessionSettings")
    call(*args, {"sessionCode": session_code, "settings": settings})
    logger.info("Applied settings to session %s", session_code)


# --- Full pipeline: skill output -> session -> DB record ---


def create_practice_for_lesson(
    teacher: Teacher,
    student: Student,
    skill_output: dict,
    lesson: Lesson | None = None,
) -> ClasstimeSession:
    """Full pipeline: skill output -> QS -> questions -> solo session -> DB.

    skill_output format (from generate-classtime-questions):
    {
        "questions": [{"source_ref": {...}, "payload_type": "gap", "payload": {...}}],
        "session_title": "Practice: Past Tense - Alex Chen (Mar 20)",
        "feedback_mode": "practice",  # optional
    }

    Returns a ClasstimeSession with all fields populated.
    """
    title = skill_output.get("session_title", "Practice session")
    questions = skill_output.get("questions", [])

    # Get per-teacher token (provisions account if needed)
    token = ensure_teacher_token(teacher)

    # 1. Create question set
    qs_id = create_question_set(title, token=token)

    # 2. Create questions, track source_ref mappings
    questions_data = []
    for q in questions:
        payload = _build_payload(q)
        q_id = create_question(qs_id, payload, token=token)
        questions_data.append(
            {
                "question_id": q_id,
                "question_set_id": qs_id,
                "source_ref": q.get("source_ref"),
                "payload_type": q.get("payload_type"),
                "title": q.get("payload", {}).get("title", ""),
            }
        )

    # 3. Create solo session (clean /code/ URL)
    secret = enable_solo(qs_id, token=token)
    student_url = create_solo_session(
        secret,
        owner_account_id=teacher.classtime_account_id,
        token=token,
    )
    code = student_url.split("/")[-1]

    # 3.5 Apply session settings (solo sessions use Classtime defaults)
    feedback_mode = skill_output.get("feedback_mode", "practice")
    settings = build_session_settings(
        title=title,
        feedback_mode=feedback_mode,
        shuffle_questions=skill_output.get("shuffle_questions", False),
        tts_language=skill_output.get("tts_language"),
    )
    # Preserve activeQuestions or solo session shows "waiting for questions"
    call_fn = proto_call_as if token else proto_call
    call_args = (token, "Session", "getSessionDetails") if token else ("Session", "getSessionDetails")
    details = call_fn(*call_args, {"code": code})
    active_qs = details.get("session", {}).get("settings", {}).get("activeQuestions", [])
    set_session_settings(code, settings, active_questions=active_qs, token=token)

    # 4. Store in DB
    session = ClasstimeSession.objects.create(
        teacher=teacher,
        student=student,
        lesson=lesson,
        session_code=code,
        question_set_id=qs_id,
        questions_data=questions_data,
        student_url=student_url,
        secret_link=secret,
        status=STATUS_CREATED,
    )

    SessionParticipant.objects.create(session=session, student=student)

    logger.info(
        "Created practice session %s for %s (%d questions): %s",
        code,
        student.name,
        len(questions_data),
        student_url,
    )
    return session


def _build_payload(question_spec: dict) -> QuestionPayload:
    """Build a QuestionPayload from skill output question spec."""
    payload_type = question_spec.get("payload_type", "")
    payload = question_spec.get("payload", {})

    if payload_type == PAYLOAD_BOOLEAN:
        return BooleanPayload(**payload)
    elif payload_type == PAYLOAD_CHOICE:
        choices = [SingleChoiceOption(**c) for c in payload.pop("choices", [])]
        return SingleChoicePayload(choices=choices, **payload)
    elif payload_type == PAYLOAD_MULTIPLE_CHOICE:
        choices = [SingleChoiceOption(**c) for c in payload.pop("choices", [])]
        return MultipleChoicePayload(choices=choices, **payload)
    elif payload_type == PAYLOAD_GAP:
        gaps = []
        for g in payload.pop("gaps", []):
            choices = [GapChoice(**c) for c in g.pop("choices", [])]
            gaps.append(Gap(choices=choices, **g))
        return GapPayload(gaps=gaps, **payload)
    elif payload_type == PAYLOAD_SORTER:
        return SorterPayload(**payload)
    elif payload_type == PAYLOAD_CATEGORIZER:
        items = [CategorizerItem(**i) for i in payload.pop("items", [])]
        return CategorizerPayload(items=items, **payload)
    else:
        raise ValueError(f"Unknown payload_type: {payload_type}")
