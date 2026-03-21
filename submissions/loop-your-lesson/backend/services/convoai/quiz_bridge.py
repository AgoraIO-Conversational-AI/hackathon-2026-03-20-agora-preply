"""Real-time quiz event processing via Pusher websockets.

Connects Classtime `binary-answer-added` events to the ConvoAI agent:
  1. Decode the Pusher binary event (protobuf)
  2. Map to the original lesson error via questions_data
  3. Update mastery state in Redis
  4. POST /speak (APPEND) - instant quiz reaction
  5. POST /update - refresh system prompt with mastery

Architecture:
  pysher runs in a background thread -> callbacks bridge to asyncio
  via loop.call_soon_threadsafe -> async handlers call ConvoAI + Redis

Protobuf decoder from: docs/classtime-api-guide.md section 10
"""

import asyncio
import base64
import logging
from typing import Any

import httpx
import pysher
from django.conf import settings

from apps.classtime_sessions.services.auth import create_user_token, provision_teacher
from services.convoai.client import get_client
from services.convoai.schemas import MasteryState
from services.convoai.session_store import get_session, mark_agent_dead, update_mastery

logger = logging.getLogger(__name__)


class QuizBridge:
    """Connect Classtime Pusher events to ConvoAI agent context.

    Lifecycle:
      1. Created when voice session starts (if classtime_session_code provided)
      2. Subscribes to Pusher channel for quiz events
      3. On each answer: decode -> update mastery -> /speak + /update
      4. Stopped when voice session ends
    """

    def __init__(
        self,
        session_id: str,
        session_code: str,
        agent_id: str,
        questions_data: dict[str, dict] | None = None,
        teacher_token: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.session_code = session_code
        self.agent_id = agent_id
        self.questions_data = questions_data or {}
        self.pusher: pysher.Pusher | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._teacher_token: str | None = teacher_token

    async def start(self) -> None:
        """Subscribe to Pusher channel, start processing quiz events."""
        self._loop = asyncio.get_running_loop()
        self._running = True

        logger.info(
            "[QUIZ_BRIDGE] Starting: session=%s code=%s agent=%s questions_data_keys=%s",
            self.session_id,
            self.session_code,
            self.agent_id,
            list(self.questions_data.keys()) if self.questions_data else "EMPTY",
        )

        # Get Pusher config
        pusher_config = await self._get_pusher_config()
        if not pusher_config:
            logger.warning("[QUIZ_BRIDGE] FAILED: Could not get Pusher config for session %s", self.session_code)
            return

        api_key = pusher_config["apiKey"]
        cluster = pusher_config.get("cluster", "eu")

        # Store teacher token for Pusher auth
        self._teacher_token = await self._get_teacher_token()

        # Connect pysher (runs in its own thread)
        self.pusher = pysher.Pusher(
            key=api_key,
            cluster=cluster,
            custom_host=f"ws-{cluster}.pusher.com",
            auth_endpoint_headers={"skip": "true"},  # we use custom_auth
        )

        self.pusher.connection.bind(
            "pusher:connection_established",
            lambda _data: self._on_connected(),
        )
        self.pusher.connection.bind(
            "pusher:error",
            lambda data: logger.warning("Pusher error: %s", data),
        )

        # Build Classtime question_id → error mapping
        await self._build_question_id_mapping()

        self.pusher.connect()
        logger.info(
            "[QUIZ_BRIDGE] Pusher connected: session=%s code=%s agent=%s questions_mapped=%d mapping=%s",
            self.session_id,
            self.session_code,
            self.agent_id,
            len(self.questions_data),
            {k: v.get("error_subtype", "?") for k, v in self.questions_data.items()},
        )

    def _on_connected(self) -> None:
        """Called when Pusher connection is established (runs in pysher thread)."""
        channel_name = f"private-teacher-session-{self.session_code}"
        logger.info("[QUIZ_BRIDGE] Pusher connected, subscribing to channel=%s", channel_name)

        # Get Pusher auth token from Classtime for the private channel
        socket_id = self.pusher.connection.socket_id  # type: ignore[union-attr]
        auth_token = self._get_pusher_auth(channel_name, socket_id)
        if not auth_token:
            logger.error("Could not get Pusher auth for %s", channel_name)
            return

        channel = self.pusher.subscribe(channel_name, auth=auth_token)  # type: ignore[union-attr]
        channel.bind("binary-answer-added", self._on_answer_event)

    def _get_pusher_auth(self, channel_name: str, socket_id: str) -> str | None:
        """Get Pusher auth signature from Classtime (sync, runs in pysher thread).

        Tries teacher token first, falls back to admin token.
        """
        tokens_to_try = []
        if self._teacher_token:
            tokens_to_try.append(("teacher", self._teacher_token))
        admin_token = getattr(settings, "CLASSTIME_ADMIN_TOKEN", "") or ""
        if admin_token.strip():
            tokens_to_try.append(("admin", admin_token.strip()))

        for label, token in tokens_to_try:
            try:
                resp = httpx.post(
                    "https://www.classtime.com/service/public/Session/getRealtimeAuthentication",
                    json={
                        "cluster": "EU",
                        "channelName": channel_name,
                        "socketId": socket_id,
                    },
                    headers={
                        "Authorization": f"JWT {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json,*/*",
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()
                auth = data.get("auth", "")
                logger.info("Pusher auth obtained via %s token for %s", label, channel_name)
                return auth
            except Exception:
                logger.debug("Pusher auth failed with %s token", label)
                continue

        logger.warning("Could not get Pusher auth with any token for %s", channel_name)
        return None

    def _on_answer_event(self, data: str) -> None:
        """Pusher callback for quiz answer (runs in pysher thread).

        Bridges to async via loop.call_soon_threadsafe.
        """
        logger.info(
            "[QUIZ_BRIDGE] Raw Pusher event received: session=%s running=%s loop=%s data_len=%d",
            self.session_id,
            self._running,
            self._loop is not None,
            len(data) if data else 0,
        )
        if not self._running or self._loop is None:
            logger.warning("[QUIZ_BRIDGE] Dropping event: running=%s loop=%s", self._running, self._loop is not None)
            return

        self._loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self._process_answer(data),
        )

    async def _process_answer(self, raw_data: str) -> None:
        """Process a quiz answer event (runs in asyncio event loop)."""
        try:
            # 1. Decode protobuf
            decoded = decode_answer_event(raw_data)
            logger.info(
                "[QUIZ_BRIDGE] Decoded event: %s",
                {k: v for k, v in decoded.items() if k != "content" or len(str(v)) < 200},
            )
            if not decoded.get("question_id"):
                logger.warning("[QUIZ_BRIDGE] Empty question_id in decoded event: %s", decoded)
                return

            logger.info(
                "[QUIZ_BRIDGE] Quiz answer: question=%s correctness=%s content=%s",
                decoded.get("question_id"),
                decoded.get("correctness"),
                decoded.get("content", "")[:100],
            )

            # 2. Check if agent is still alive
            session = await get_session(self.session_id)
            if not session:
                logger.warning("[QUIZ_BRIDGE] Session %s not found in store, skipping", self.session_id)
                return
            if not session.get("agent_alive", True):
                logger.warning("[QUIZ_BRIDGE] Agent dead for session %s, skipping quiz event", self.session_id)
                return

            # 3. Map to source error
            error_subtype = self._map_to_error(decoded)
            is_correct = decoded.get("correctness") == "CORRECT"
            logger.info(
                "[QUIZ_BRIDGE] Mapped: question=%s -> error_subtype=%s is_correct=%s (available_keys=%s)",
                decoded.get("question_id"),
                error_subtype,
                is_correct,
                list(self.questions_data.keys())[:5],
            )

            # 4. Update mastery state in Redis
            mastery: MasteryState = session["mastery"]
            self._update_mastery(mastery, error_subtype, is_correct, decoded)
            await update_mastery(self.session_id, mastery)
            logger.info(
                "[QUIZ_BRIDGE] Mastery updated: summary=%s",
                mastery.summary,
            )

            # 5. Instant reaction via /speak (APPEND - queued after current speech)
            from services.convoai.views import reconstruct_context

            context = reconstruct_context(session["context_args"])
            speak_text = context.format_speak_quiz_reaction(error_subtype, is_correct)
            client = get_client()

            logger.info("[QUIZ_BRIDGE] Calling /speak: agent=%s text=%s", self.agent_id, speak_text)
            try:
                await client.speak(self.agent_id, speak_text)
                logger.info("[QUIZ_BRIDGE] /speak succeeded for agent=%s", self.agent_id)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[QUIZ_BRIDGE] /speak FAILED: agent=%s status=%s body=%s",
                    self.agent_id,
                    e.response.status_code,
                    e.response.text[:200],
                )
                await mark_agent_dead(self.session_id)
                return

            # 6. Refresh system prompt via /update
            enriched_prompt = context.build_enriched_prompt(mastery)
            logger.info(
                "[QUIZ_BRIDGE] Calling /update: agent=%s prompt_len=%d",
                self.agent_id,
                len(enriched_prompt),
            )
            try:
                await client.update_agent(self.agent_id, enriched_prompt)
                logger.info("[QUIZ_BRIDGE] /update succeeded for agent=%s", self.agent_id)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[QUIZ_BRIDGE] /update FAILED: agent=%s status=%s body=%s",
                    self.agent_id,
                    e.response.status_code,
                    e.response.text[:200],
                )
                await mark_agent_dead(self.session_id)

        except Exception:
            logger.exception("[QUIZ_BRIDGE] Error processing quiz answer for session %s", self.session_id)

    async def _build_question_id_mapping(self) -> None:
        """Fetch session details from Classtime to map question UUIDs to error subtypes.

        questions_data starts keyed by index ("0", "1", ...) from questions.json.
        We fetch getSessionDetails to get the ordered list of Classtime question IDs,
        then re-key questions_data by those IDs.
        """
        if not self.questions_data or not self._teacher_token:
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://www.classtime.com/service/public/Session/getSessionDetails",
                    json={"code": self.session_code},
                    headers={
                        "Authorization": f"JWT {self._teacher_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json,*/*",
                    },
                )
                resp.raise_for_status()
                details = resp.json()

            # Extract question IDs in order from session details
            questions_map = details.get("questions", {})
            if not questions_map:
                logger.info("No questions in session details, keeping index-based mapping")
                return

            # questions_map is {question_id: question_data} — preserve insertion order
            ct_question_ids = list(questions_map.keys())
            remapped: dict[str, dict] = {}
            for i, ct_id in enumerate(ct_question_ids):
                idx_key = str(i)
                if idx_key in self.questions_data:
                    remapped[ct_id] = self.questions_data[idx_key]

            if remapped:
                self.questions_data = remapped
                logger.info(
                    "Mapped %d Classtime question IDs to error subtypes",
                    len(remapped),
                )
            else:
                logger.info("Could not map Classtime IDs, keeping index-based mapping")

        except Exception:
            logger.warning("Could not fetch session details for question mapping", exc_info=True)

    def _map_to_error(self, decoded: dict) -> str:
        """Map a quiz question_id to the source error subtype."""
        question_id = decoded.get("question_id", "")
        if question_id in self.questions_data:
            subtype = self.questions_data[question_id].get("error_subtype", "unknown")
            logger.info("[QUIZ_BRIDGE] _map_to_error: exact match question_id=%s -> %s", question_id, subtype)
            return subtype
        # Fallback: try matching by answer index (if questions_data is still index-keyed)
        logger.warning(
            "[QUIZ_BRIDGE] _map_to_error: NO exact match for question_id=%s in keys=%s, trying fallback",
            question_id,
            list(self.questions_data.keys()),
        )
        for entry in self.questions_data.values():
            if entry.get("error_subtype") != "unknown":
                logger.info("[QUIZ_BRIDGE] _map_to_error: fallback -> %s", entry["error_subtype"])
                return entry["error_subtype"]
        logger.warning("[QUIZ_BRIDGE] _map_to_error: no mapping found, returning 'unknown'")
        return "unknown"

    def _update_mastery(
        self,
        mastery: MasteryState,
        error_subtype: str,
        is_correct: bool,
        raw_event: dict,
    ) -> None:
        """Update mastery state for the matched error."""
        for err in mastery.errors:
            if err.subtype == error_subtype:
                err.quiz_result = raw_event.get("correctness", "UNKNOWN")
                err.quiz_answer = raw_event.get("content", "")
                err.focus_level = "low" if is_correct else "critical"
                break

        # Add to quiz events trail
        mastery.quiz_events.append(
            {
                "question_id": raw_event.get("question_id", ""),
                "correctness": raw_event.get("correctness", "UNKNOWN"),
                "question_title": error_subtype.replace("_", " ").title(),
            }
        )

        # Update summary
        tested = sum(1 for e in mastery.errors if e.quiz_result is not None)
        correct = sum(1 for e in mastery.errors if e.quiz_result == "CORRECT")
        wrong = sum(1 for e in mastery.errors if e.quiz_result == "WRONG")
        mastery.summary = {
            "tested": tested,
            "correct": correct,
            "wrong": wrong,
            "untested": len(mastery.errors) - tested,
            "current_focus": [e.subtype for e in mastery.errors if e.focus_level in ("high", "critical")],
        }

    async def _get_pusher_config(self) -> dict[str, Any] | None:
        """Get Pusher API key and cluster from Classtime.

        Mints a teacher token dynamically from the admin token if needed.
        """
        token = await self._get_teacher_token()
        if not token:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://www.classtime.com/service/public/Session/getPusherConfig",
                    json={"sessionCode": self.session_code},
                    headers={
                        "Authorization": f"JWT {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json,*/*",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("Pusher config: apiKey=%s cluster=%s", data.get("apiKey"), data.get("cluster"))
                return data
        except Exception:
            logger.warning(
                "Could not fetch Pusher config from Classtime",
                exc_info=True,
            )
            return None

    async def _get_teacher_token(self) -> str | None:
        """Get a teacher token for Pusher auth.

        Priority:
        1. Per-teacher token passed at construction (from Teacher model cache)
        2. Static CLASSTIME_TEACHER_TOKEN setting (legacy)
        3. Mint from admin token (fallback)
        """
        # 1. Per-teacher token (set from the lesson's teacher via ensure_teacher_token)
        if self._teacher_token:
            return self._teacher_token

        # 2. Static setting (legacy)
        token = getattr(settings, "CLASSTIME_TEACHER_TOKEN", "") or ""
        if token.strip():
            return token.strip()

        # 3. Mint dynamically from admin token
        admin_token = getattr(settings, "CLASSTIME_ADMIN_TOKEN", "") or ""
        if not admin_token.strip():
            logger.info("No CLASSTIME_ADMIN_TOKEN set, skipping quiz bridge Pusher")
            return None

        try:
            account_id = provision_teacher(
                subject="preply-demo-teacher",
                email="demo-teacher@preply.com",
                first_name="Demo",
                last_name="Teacher",
            )
            token, expires_at = create_user_token(account_id)
            logger.info("Minted teacher token (expires %s)", expires_at)
            return token
        except Exception:
            logger.warning("Could not mint teacher token", exc_info=True)
            return None

    async def stop(self) -> None:
        """Disconnect Pusher, cleanup."""
        self._running = False
        if self.pusher:
            self.pusher.disconnect()
            self.pusher = None
        logger.info("QuizBridge stopped for session %s", self.session_id)


# --- Protobuf decoder (from classtime-api-guide.md section 10) ---


def decode_answer_event(b64_data: str) -> dict[str, Any]:
    """Decode binary-answer-added Pusher event to structured dict."""
    raw = base64.b64decode(b64_data)
    outer = _decode_fields(raw)

    # Field 4 = AnswerSummary
    summary_bytes = outer.get(4, (None, b""))[1]
    if not isinstance(summary_bytes, bytes):
        return {}
    summary = _decode_fields(summary_bytes)

    result: dict[str, Any] = {
        "answer_id": summary[1][1].decode() if 1 in summary else "",
        "participant_id": summary[2][1].decode() if 2 in summary else "",
        "question_id": summary[4][1].decode() if 4 in summary else "",
        "content": summary[3][1].decode() if 3 in summary else "",
    }

    # Field 11 = Evaluation
    if 11 in summary:
        ev_bytes = summary[11][1]
        if isinstance(ev_bytes, bytes):
            ev = _decode_fields(ev_bytes)
            correctness_map = {0: "CORRECT", 1: "PARTIALLY_CORRECT", 2: "WRONG"}
            correctness_val = ev.get(9, (None, 0))[1]
            result["correctness"] = correctness_map.get(correctness_val, "UNKNOWN")
            if 2 in ev:
                gp_bytes = ev[2][1]
                if isinstance(gp_bytes, bytes):
                    gp = _decode_fields(gp_bytes)
                    result["points_centis"] = gp.get(1, (None, 0))[1]

    return result


def _decode_fields(data: bytes) -> dict[int, tuple[str, Any]]:
    """Minimal protobuf wire-format decoder."""
    fields: dict[int, tuple[str, Any]] = {}
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


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    """Read a variable-length integer from protobuf wire format."""
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
