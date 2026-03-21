# ruff: noqa: E402
#!/usr/bin/env python3
"""Test Pusher websocket connection to Classtime session events.

Usage:
    # With an existing session code:
    uv run python -u scripts/test_pusher.py --session-code ABC123

    # Create a test session first, then listen:
    uv run python -u scripts/test_pusher.py --create-session

Channels:
    private-teacher-session-{CODE} - binary-answer-added, binary-participant-added
    presence-session-{CODE} - member_added/removed (JSON)

Answer data is base64-encoded protobuf. Use --decode to attempt decoding.
"""

import argparse
import base64
import json
import logging
import os
import sys
import time

import django
from dotenv import load_dotenv

# Load .env from backend/ directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(backend_dir, ".env"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
sys.path.insert(0, backend_dir)
django.setup()

from datetime import UTC

import httpx
import pysher

from apps.classtime_sessions.services.client import (
    CLASSTIME_PROTO_BASE,
    _proto_headers,
    _proto_headers_for,
    proto_call,
    proto_call_as,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Suppress noisy pysher connection logs
logging.getLogger("pysher.connection").setLevel(logging.WARNING)


# --- Classtime Pusher API ---


def get_pusher_config(session_code: str, token: str | None = None) -> dict:
    """Call Session/getPusherConfig to get Pusher credentials."""
    if token:
        resp = proto_call_as(token, "Session", "getPusherConfig", {"sessionCode": session_code})
    else:
        resp = proto_call("Session", "getPusherConfig", {"sessionCode": session_code})
    return resp


def get_realtime_auth(cluster: str, channel_name: str, socket_id: str, token: str | None = None) -> dict:
    """Call Session/getRealtimeAuthentication to auth a channel subscription."""
    cluster_map = {"eu": "EU", "us": "US", "soketi": "SOKETI", "EU": "EU", "US": "US", "SOKETI": "SOKETI"}
    cluster_value = cluster_map.get(cluster, cluster)

    url = f"{CLASSTIME_PROTO_BASE}/Session/getRealtimeAuthentication"
    body = {
        "cluster": cluster_value,
        "channelName": channel_name,
        "socketId": socket_id,
    }
    headers = _proto_headers_for(token) if token else _proto_headers()
    resp = httpx.post(url, json=body, headers=headers, timeout=30)
    data = resp.json()
    if "classtimeErrorCode" in data:
        logger.error("Auth FAILED for %s: %s", channel_name, data.get("message", "?"))
        return {}
    return data


PUSHER_CLUSTER_MAP = {"EU": "eu", "US": "us", "SOKETI": "eu", "eu": "eu", "us": "us"}


# --- Token helper ---


def _get_teacher_token() -> str:
    """Get a teacher token, minting one via admin API if needed."""
    from django.conf import settings as django_settings

    token = getattr(django_settings, "CLASSTIME_TEACHER_TOKEN", "") or os.environ.get("CLASSTIME_TEACHER_TOKEN", "")
    if token:
        return token

    logger.info("CLASSTIME_TEACHER_TOKEN not set. Minting via admin token...")
    from apps.classtime_sessions.services.auth import _admin_proto_call

    resp = _admin_proto_call(
        "Account",
        "getOrCreateAccount",
        {
            "role": "TEACHER",
            "user_profile": {"first_name": "Pusher", "last_name": "Test"},
            "subject": "pusher-test-teacher",
            "email": "pusher-test@preply-hackathon.local",
        },
    )
    account_id = resp.get("accountId") or resp.get("account_id")

    org_id = getattr(django_settings, "CLASSTIME_ORG_ID", "") or os.environ.get("CLASSTIME_ORG_ID", "")
    if org_id:
        _admin_proto_call(
            "Account",
            "associateMember",
            {
                "organization_id": org_id,
                "account_id": account_id,
            },
        )

    token_resp = _admin_proto_call("Account", "createToken", {"classtime_id": account_id})
    token = token_resp["token"]
    django_settings.CLASSTIME_TEACHER_TOKEN = token
    return token


# --- Test session creation ---


def create_test_session() -> tuple[str, str]:
    """Create a minimal Classtime session for testing."""
    from apps.classtime_sessions.services.questions import create_question, create_question_set
    from apps.classtime_sessions.services.schemas import BooleanPayload, Gap, GapPayload
    from apps.classtime_sessions.services.sessions import (
        create_practice_session,
        create_solo_session,
        enable_solo,
    )

    token = _get_teacher_token()

    logger.info("Creating test question set...")
    qs_id = create_question_set("Pusher Test Session", token=token)

    q1 = GapPayload(
        title="Fill in the past tense",
        template_text="Yesterday I {0} to the cinema.",
        gaps=[Gap(type="blank", solution="went")],
    )
    create_question(qs_id, q1, token=token)

    q2 = BooleanPayload(
        title="'She don't like coffee' is correct English.",
        is_correct=False,
        explanation="Correct form: She doesn't like coffee.",
    )
    create_question(qs_id, q2, token=token)

    try:
        logger.info("Creating solo session...")
        secret = enable_solo(qs_id, token=token)
        student_url = create_solo_session(secret, token=token)
        code = student_url.split("/")[-1]
    except Exception as e:
        logger.warning("Solo session failed (%s), trying regular session...", e)
        code = create_practice_session(qs_id, "Pusher Test", token=token)
        student_url = f"https://www.classtime.com/student/login/{code}"

    logger.info("Session code: %s", code)
    logger.info("Student URL:  %s", student_url)
    return code, student_url


# --- Binary protobuf decoding (best-effort) ---


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


def _decode_fields(data: bytes) -> dict:
    """Minimal protobuf wire-format decoder."""
    fields = {}
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        field_num = tag >> 3
        wire_type = tag & 0x7
        if wire_type == 0:
            val, pos = _read_varint(data, pos)
            fields[field_num] = ("varint", val)
        elif wire_type == 2:
            length, pos = _read_varint(data, pos)
            fields[field_num] = ("bytes", data[pos : pos + length])
            pos += length
        elif wire_type == 5:
            fields[field_num] = ("32bit", int.from_bytes(data[pos : pos + 4], "little"))
            pos += 4
        elif wire_type == 1:
            fields[field_num] = ("64bit", int.from_bytes(data[pos : pos + 8], "little"))
            pos += 8
    return fields


CORRECTNESS_MAP = {0: "CORRECT", 1: "PARTIALLY_CORRECT", 2: "WRONG"}


def decode_answer_event(b64_data: str) -> dict:
    """Decode binary-answer-added Pusher event to structured dict.

    Proto structure: PusherAnswerAdded { field 4: AnswerSummary, field 5: Timestamp }
    AnswerSummary: { 1: id, 2: participant_id, 3: content, 4: question_id,
                     11: Evaluation, 13: created_at }
    Evaluation: { 2: grading_points, 5: gap_evaluations[], 9: correctness }
    """
    try:
        raw = base64.b64decode(b64_data)
        outer = _decode_fields(raw)

        # Field 4 = AnswerSummary
        if 4 not in outer:
            return {"error": "no AnswerSummary in event"}
        summary = _decode_fields(outer[4][1])

        result = {
            "answer_id": summary[1][1].decode() if 1 in summary else "",
            "participant_id": summary[2][1].decode() if 2 in summary else "",
            "question_id": summary[4][1].decode() if 4 in summary else "",
            "content": summary[3][1].decode() if 3 in summary else "",
            "correctness": "UNKNOWN",
            "points_centis": 0,
        }

        # Field 11 = Evaluation
        if 11 in summary:
            ev = _decode_fields(summary[11][1])
            result["correctness"] = CORRECTNESS_MAP.get(ev.get(9, (None, 0))[1], "UNKNOWN")
            if 2 in ev:
                gp = _decode_fields(ev[2][1])
                result["points_centis"] = gp.get(1, (None, 0))[1] if 1 in gp else 0

        # Field 13 = created_at (Timestamp)
        if 13 in summary:
            from datetime import datetime

            ts = _decode_fields(summary[13][1])
            seconds = ts.get(1, (None, 0))[1] if 1 in ts else 0
            if seconds:
                result["answered_at"] = datetime.fromtimestamp(seconds, tz=UTC).isoformat()

        return result
    except Exception as e:
        return {"error": str(e), "raw": b64_data[:100]}


# --- Event handlers ---


def enrich_answer(session_code: str, decoded: dict, questions_data: list[dict]) -> dict:
    """Enrich a decoded Pusher answer event with question context and student response.

    Calls Classtime APIs to get:
    - Question title, type, and content
    - What the student actually typed/selected
    - Which lesson error this question tests (via source_ref)

    Returns a rich context dict suitable for AI agent injection.
    """
    from apps.classtime_sessions.services.results import get_detailed_answers
    from apps.classtime_sessions.services.sessions import get_session_details

    question_id = decoded.get("question_id", "")
    _ = decoded.get("answer_id", "")

    # Get session details for question info
    details = get_session_details(session_code)
    ct_questions = details.get("questions", {})

    q_info = ct_questions.get(question_id, {}).get("questionInfo", {})
    title = q_info.get("title", "")
    kind = q_info.get("kind", "").lower()

    # Map session question_id back to library question_id → source_ref
    derived_from = ct_questions.get(question_id, {}).get("derivedFromQuestionRef", {}).get("id", "")
    source_ref = None
    for qd in questions_data:
        if qd.get("question_id") == derived_from:
            source_ref = qd.get("source_ref")
            break

    # Get what the student actually answered
    student_answer = ""
    try:
        detailed = get_detailed_answers(session_code, question_id)
        if detailed:
            raw_answer = detailed[0].get("answer", {})
            # Extract answer based on type and infer kind if missing
            if "answerGap" in raw_answer:
                gaps = raw_answer["answerGap"].get("gaps", [])
                student_answer = ", ".join(g.get("content", "?") for g in gaps)
                if not kind:
                    kind = "gap"
            elif "answerBoolean" in raw_answer:
                student_answer = "True" if raw_answer["answerBoolean"].get("isTrue") else "False"
                if not kind:
                    kind = "true_false"
            elif "answerSingleChoice" in raw_answer:
                student_answer = str(raw_answer["answerSingleChoice"].get("selectedChoice", "?"))
                if not kind:
                    kind = "single_choice"
            elif "answerSorter" in raw_answer:
                student_answer = str(raw_answer["answerSorter"].get("sortedChoices", []))
                if not kind:
                    kind = "sorter"
            elif "answerCategorizer" in raw_answer:
                student_answer = str(raw_answer["answerCategorizer"].get("selectedCategories", {}))
                if not kind:
                    kind = "categorizer"
            elif "answerText" in raw_answer:
                student_answer = raw_answer["answerText"].get("content", "")
                if not kind:
                    kind = "text"
    except Exception as e:
        logger.debug("Could not get detailed answer: %s", e)

    return {
        "question_id": question_id,
        "question_title": title,
        "question_type": kind or "unknown",
        "correctness": decoded.get("correctness", "UNKNOWN"),
        "points_centis": decoded.get("points_centis", 0),
        "student_answer": student_answer,
        "source_ref": source_ref,
        "answered_at": decoded.get("answered_at", ""),
    }


def format_for_ai(enriched: dict, question_number: int, total_questions: int) -> str:
    """Format an enriched answer as context for the ConvoAI agent."""
    correctness = enriched["correctness"]
    emoji = "CORRECT" if correctness == "CORRECT" else "WRONG"
    title = enriched["question_title"]
    q_type = enriched["question_type"]
    student = enriched["student_answer"]
    source = enriched.get("source_ref")

    parts = [f"[Quiz Update] Q{question_number}/{total_questions} '{title}' ({q_type}): {emoji}."]

    if student:
        parts.append(f"Student answered: '{student}'.")

    if source:
        error_type = source.get("error_type", "")
        subtype = source.get("subtype", "")
        if error_type:
            parts.append(f"Tests error: {error_type}/{subtype}." if subtype else f"Tests error: {error_type}.")

    return " ".join(parts)


# Track answers per session for numbering
_answer_count = {}


def on_binary_answer(data):
    """Handle binary-answer-added event."""
    if not isinstance(data, str):
        return

    decoded = decode_answer_event(data)
    if "error" in decoded:
        logger.info(">>> ANSWER (decode error): %s", decoded["error"])
        return

    question_id = decoded.get("question_id", "?")
    correctness = decoded.get("correctness", "?")
    points = decoded.get("points_centis", 0)
    answered_at = decoded.get("answered_at", "?")

    logger.info(">>> ANSWER ADDED")
    logger.info("    question_id:  %s", question_id)
    logger.info("    correctness:  %s", correctness)
    logger.info("    points:       %s centis", points)
    logger.info("    answered_at:  %s", answered_at)

    # Enrich with question context (requires session_code from outer scope)
    if _current_session_code:
        try:
            enriched = enrich_answer(_current_session_code, decoded, _current_questions_data)
            _answer_count[_current_session_code] = _answer_count.get(_current_session_code, 0) + 1
            ai_context = format_for_ai(enriched, _answer_count[_current_session_code], _total_questions)

            logger.info("")
            logger.info("    --- ENRICHED ---")
            logger.info("    title:          %s", enriched["question_title"])
            logger.info("    type:           %s", enriched["question_type"])
            logger.info("    student_answer: %s", enriched["student_answer"])
            logger.info("    source_ref:     %s", enriched.get("source_ref"))
            logger.info("")
            logger.info("    --- FOR AI AGENT ---")
            logger.info("    %s", ai_context)
            logger.info("")
        except Exception as e:
            logger.warning("    Enrichment failed: %s", e)


# Globals set by main() for the event handler
_current_session_code = ""
_current_questions_data = []
_total_questions = 0


def on_binary_participant(data):
    """Handle binary-participant-added event."""
    logger.info(">>> PARTICIPANT JOINED")
    if isinstance(data, str):
        try:
            raw = base64.b64decode(data)
            # Extract printable strings for participant name
            strings = []
            current = []
            for byte in raw:
                if 32 <= byte < 127:
                    current.append(chr(byte))
                else:
                    if len(current) >= 2:
                        strings.append("".join(current))
                    current = []
            if len(current) >= 2:
                strings.append("".join(current))
            logger.info("    Participant data: %s", strings[:5])
        except Exception:
            logger.info("    Raw: %s", data[:200])


def on_member_added(data):
    """Handle presence channel member_added event."""
    parsed = json.loads(data) if isinstance(data, str) else data
    user_info = parsed.get("user_info", {}).get("data", {})
    name = user_info.get("name", user_info.get("firstName", "?"))
    role = parsed.get("user_info", {}).get("role", "?")
    logger.info(">>> MEMBER JOINED: %s (%s)", name, role)


def on_any_event(channel_name, event_name, data):
    """Catch-all for any event."""
    if event_name.startswith("pusher:") or event_name.startswith("pusher_internal:"):
        return
    logger.info(">>> EVENT [%s] on [%s]", event_name, channel_name)
    if isinstance(data, str) and data.startswith("{"):
        logger.info("    JSON: %s", data[:300])
    elif isinstance(data, str):
        logger.info("    Binary: [%d bytes base64]", len(data))
    else:
        logger.info("    Data: %s", str(data)[:300])


# --- Main ---


def main():
    parser = argparse.ArgumentParser(description="Test Pusher connection to Classtime")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session-code", help="Existing session code to listen to")
    group.add_argument("--create-session", action="store_true", help="Create a test session first")
    args = parser.parse_args()

    token = _get_teacher_token()

    if args.create_session:
        session_code, student_url = create_test_session()
    else:
        session_code = args.session_code
        student_url = f"https://www.classtime.com/student/login/{session_code}"

    # Set globals for event handlers
    global _current_session_code, _current_questions_data, _total_questions
    _current_session_code = session_code

    # Load questions_data if we have a DB session, otherwise empty
    try:
        from apps.classtime_sessions.models import ClasstimeSession

        db_session = ClasstimeSession.objects.filter(session_code=session_code).first()
        _current_questions_data = db_session.questions_data if db_session else []
    except Exception:
        _current_questions_data = []

    # Get total question count from session details
    try:
        from apps.classtime_sessions.services.sessions import get_session_details

        details = get_session_details(session_code)
        active_qs = details.get("session", {}).get("settings", {}).get("activeQuestions", [])
        _total_questions = len(active_qs)
        logger.info("Session has %d questions", _total_questions)
    except Exception:
        _total_questions = 0

    # Step 1: Get Pusher config
    config = get_pusher_config(session_code, token=token)
    api_key = config.get("apiKey", "")
    cluster_raw = config.get("cluster", "EU")
    cluster = PUSHER_CLUSTER_MAP.get(cluster_raw, "eu")

    if not api_key:
        logger.error("No API key from getPusherConfig: %s", config)
        sys.exit(1)

    logger.info("Pusher: cluster=%s, key=%s...", cluster, api_key[:8])

    # Step 2: Channels to subscribe
    channels = {
        f"private-teacher-session-{session_code}": "private",  # answer + participant events (binary)
        f"presence-session-{session_code}": "presence",  # member join/leave (JSON)
        f"private-session-{session_code}": "private",  # original guess (keep for comparison)
    }

    # Step 3: Connect with custom auth
    class ClasstimePusher(pysher.Pusher):
        def _generate_auth_token(self, channel_name):
            socket_id = self.connection.socket_id
            auth_data = get_realtime_auth(cluster_raw, channel_name, socket_id, token=token)
            auth_str = auth_data.get("auth", "")
            channel_data = auth_data.get("channelData", "")
            if not auth_str:
                logger.warning("Auth returned empty for %s", channel_name)
                return ""
            logger.info("Auth OK: %s", channel_name)
            # For presence channels, return auth:channel_data
            if channel_data and channel_name.startswith("presence-"):
                return auth_str + "\n" + channel_data
            return auth_str

    pusher = ClasstimePusher(key=api_key, cluster=cluster)

    # Log all raw websocket messages for debugging
    original_on_message = pusher.connection._on_message

    def log_raw(ws, message):
        parsed = json.loads(message)
        event = parsed.get("event", "?")
        channel = parsed.get("channel", "")
        if not event.startswith("pusher:"):
            if event == "pusher_internal:subscription_succeeded":
                logger.info("Subscribed: %s", channel)
            elif event == "pusher_internal:member_added":
                logger.info("Member added on %s", channel)
            else:
                logger.info("RAW [%s] %s: %s", channel, event, str(parsed.get("data", ""))[:200])
        original_on_message(ws, message)

    pusher.connection._on_message = log_raw

    def on_connect(data):
        logger.info("Connected to Pusher!")

        for channel_name, ch_type in channels.items():
            try:
                ch = pusher.subscribe(channel_name)

                # Bind specific events
                ch.bind("binary-answer-added", on_binary_answer)
                ch.bind("binary-participant-added", on_binary_participant)

                # JSON events (proto-style names, just in case)
                ch.bind("PusherAnswerAdded", lambda d, c=channel_name: on_any_event(c, "PusherAnswerAdded", d))
                ch.bind(
                    "PusherSessionParticipantAdded",
                    lambda d, c=channel_name: on_any_event(c, "PusherSessionParticipantAdded", d),
                )

                # Presence events
                ch.bind("pusher_internal:member_added", on_member_added)

                logger.info("Bound events on %s (%s)", channel_name, ch_type)
            except Exception as e:
                logger.error("Subscribe failed for %s: %s", channel_name, e)

        print()
        print("=" * 60)
        print("LISTENING FOR EVENTS")
        print("=" * 60)
        print()
        print(f"Answer the questions at: {student_url}")
        print()
        print("Press Ctrl+C to stop.")

    def on_error(data):
        logger.error("Pusher error: %s", data)

    pusher.connection.bind("pusher:connection_established", on_connect)
    pusher.connection.bind("pusher:error", on_error)
    pusher.connect()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        pusher.disconnect()


if __name__ == "__main__":
    main()
