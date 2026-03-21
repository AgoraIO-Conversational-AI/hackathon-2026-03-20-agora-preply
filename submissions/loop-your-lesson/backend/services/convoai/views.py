"""Voice practice session API views.

These are async Django views (not DRF viewsets) because ConvoAI
client uses httpx async. Wired into config/api_urls.py.
"""

import asyncio
import json
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from apps.classtime_sessions.models import ClasstimeSession
from apps.classtime_sessions.services.auth import ensure_teacher_token
from services.agora.tokens import generate_channel_name, generate_rtc_token
from services.convoai.client import STUDENT_UID, get_client
from services.convoai.context import VoicePracticeContext
from services.convoai.quiz_bridge import QuizBridge
from services.convoai.schemas import (
    AgentResponse,
    ErrorDetail,
    LanguagePair,
    LevelSummary,
    MasteryError,
    MasteryState,
    QuizQuestionSummary,
    ThemeDetail,
    VoiceSessionResponse,
    VoiceSessionStart,
)
from services.convoai.session_store import (
    delete_session,
    get_session,
    save_session,
)

logger = logging.getLogger(__name__)

# Track active quiz bridges for cleanup on session stop
_bridges: dict[str, QuizBridge] = {}


class VoiceSessionStartView(View):
    """POST /api/v1/voice-sessions/ — Start a voice practice session."""

    async def post(self, request):  # type: ignore[override]
        try:
            body = json.loads(request.body)
            params = VoiceSessionStart.model_validate(body)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

        # Load student + lesson data from DB (or seeded data for hackathon)
        logger.info(
            "[SESSION_START] Starting voice session: student=%s lesson=%s classtime_code=%s",
            params.student_id,
            params.lesson_id,
            params.classtime_session_code or "NONE",
        )
        ctx = await _load_lesson_context(params.student_id, params.lesson_id)

        # Load raw markdown files for full context
        raw_lesson_context = _load_raw_lesson_context(params.lesson_id)
        logger.info(
            "[SESSION_START] Loaded context: student=%s level=%s errors=%d themes=%d raw_context=%d chars",
            ctx["student_name"],
            ctx["student_level"],
            len(ctx["errors"]),
            len(ctx["themes"]),
            len(raw_lesson_context),
        )

        # Build context and system prompt
        context = VoicePracticeContext(
            student_name=ctx["student_name"],
            student_level=ctx["student_level"],
            language_pair=ctx["language_pair"],
            errors=ctx["errors"],
            themes=ctx["themes"],
            questions=ctx["questions"],
            level_summary=ctx["level_summary"],
            raw_lesson_context=raw_lesson_context,
        )
        system_prompt = context.build_initial_prompt()
        greeting = context.build_greeting()

        # Generate channel and RTC tokens
        channel = generate_channel_name(params.student_id, params.lesson_id)
        student_token = generate_rtc_token(channel, STUDENT_UID)
        agent_token = generate_rtc_token(channel, 100)

        # Start ConvoAI agent
        client = get_client()
        try:
            agent: AgentResponse = await client.start_agent(
                channel=channel,
                agent_token=agent_token,
                system_prompt=system_prompt,
                greeting=greeting,
            )
        except Exception as e:
            logger.exception("Failed to start ConvoAI agent: %s", e)
            return JsonResponse({"error": f"Failed to start agent: {e}"}, status=502)

        # Store session state in Redis
        session_id = str(uuid.uuid4())
        mastery = MasteryState(
            errors=[
                MasteryError(
                    error_type=err.error_type,
                    subtype=err.subtype,
                    original=err.original,
                    corrected=err.corrected,
                )
                for err in ctx["errors"]
            ],
        )

        # Store context constructor args (VoicePracticeContext has methods, not serializable)
        context_args = {
            "student_name": ctx["student_name"],
            "student_level": ctx["student_level"],
            "language_pair": ctx["language_pair"].model_dump(),
            "errors": [e.model_dump() for e in ctx["errors"]],
            "themes": [t.model_dump() for t in ctx["themes"]],
            "questions": [q.model_dump() for q in ctx["questions"]],
            "level_summary": ctx["level_summary"].model_dump() if ctx["level_summary"] else None,
            "raw_lesson_context": raw_lesson_context,
        }

        await save_session(
            session_id,
            agent_id=agent.agent_id,
            channel=channel,
            student_id=params.student_id,
            lesson_id=params.lesson_id,
            classtime_session_code=params.classtime_session_code,
            mastery=mastery,
            context_args=context_args,
        )

        # Start quiz bridge if Classtime session code provided
        if params.classtime_session_code:
            questions_data = _load_questions_data(params.lesson_id)
            logger.info(
                "[SESSION_START] Quiz bridge setup: classtime_code=%s lesson_id=%s questions_data=%s",
                params.classtime_session_code,
                params.lesson_id,
                {k: v.get("error_subtype", "?") for k, v in questions_data.items()} if questions_data else "EMPTY",
            )

            # Get per-teacher Classtime JWT for Pusher auth
            teacher_token = None
            try:
                ct_session = await ClasstimeSession.objects.select_related("teacher").aget(
                    session_code=params.classtime_session_code,
                )
                teacher_token = ensure_teacher_token(ct_session.teacher)
                logger.info("[SESSION_START] Using per-teacher token for %s", ct_session.teacher.name)
            except Exception:
                logger.warning("[SESSION_START] Could not get per-teacher token, will fall back", exc_info=True)

            bridge = QuizBridge(
                session_id=session_id,
                session_code=params.classtime_session_code,
                agent_id=agent.agent_id,
                questions_data=questions_data,
                teacher_token=teacher_token,
            )
            _bridges[session_id] = bridge
            task = asyncio.create_task(bridge.start())
            # Prevent garbage collection of the task
            task.add_done_callback(lambda t: logger.info(
                "[SESSION_START] Quiz bridge task completed: session=%s exception=%s",
                session_id,
                t.exception() if not t.cancelled() and t.exception() else "none",
            ))
            logger.info("[SESSION_START] Quiz bridge task created for session %s", session_id)
        else:
            logger.info(
                "[SESSION_START] No classtime_session_code provided, skipping quiz bridge. "
                "student=%s lesson=%s",
                params.student_id,
                params.lesson_id,
            )

        response = VoiceSessionResponse(
            session_id=session_id,
            channel_name=channel,
            rtc_token=student_token,
            uid=STUDENT_UID,
            agent_id=agent.agent_id,
            agora_app_id=settings.AGORA_APP_ID,
            student_name=ctx["student_name"],
            student_level=ctx["student_level"],
        )
        return JsonResponse(response.model_dump(), status=201)


class VoiceSessionStatusView(View):
    """GET /api/v1/voice-sessions/{session_id}/ — Get session status."""

    async def get(self, request, session_id: str):  # type: ignore[override]
        session = await get_session(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        client = get_client()
        try:
            status = await client.get_status(session["agent_id"])
            return JsonResponse(
                {
                    "session_id": session_id,
                    "agent_id": session["agent_id"],
                    "agent_status": status.status,
                    "channel": session["channel"],
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)


class VoiceSessionStopView(View):
    """POST /api/v1/voice-sessions/{session_id}/stop/ — Stop session."""

    async def post(self, request, session_id: str):  # type: ignore[override]
        session = await get_session(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        # Stop quiz bridge if active
        bridge = _bridges.pop(session_id, None)
        if bridge:
            await bridge.stop()

        client = get_client()
        try:
            await client.stop_agent(session["agent_id"])
        except Exception as e:
            logger.warning("Error stopping agent: %s", e)

        # Persist final mastery state for teacher briefing
        mastery: MasteryState = session["mastery"]

        # Save to DB for teacher briefing
        try:
            from django.utils import timezone

            from apps.voice_sessions.models import VoiceSession

            await VoiceSession.objects.acreate(
                student_id=session["student_id"],
                lesson_id=session["lesson_id"],
                agent_id=session["agent_id"],
                channel=session["channel"],
                classtime_session_code=session.get("classtime_session_code", ""),
                mastery_snapshot=mastery.model_dump(),
                ended_at=timezone.now(),
            )
        except Exception:
            logger.warning("Could not persist VoiceSession to DB", exc_info=True)

        result = {
            "session_id": session_id,
            "stopped": True,
            "mastery_summary": mastery.summary,
            "quiz_events_count": len(mastery.quiz_events),
        }
        await delete_session(session_id)
        return JsonResponse(result)


class VoiceSessionFrameView(View):
    """POST /api/v1/voice-sessions/{session_id}/frame/ — Webcam frame for video biomarkers."""

    async def post(self, request, session_id: str):  # type: ignore[override]
        session = await get_session(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        frame_bytes = request.body
        if not frame_bytes:
            return JsonResponse({"error": "No frame data"}, status=400)

        logger.debug("Received frame for session %s (%d bytes)", session_id, len(frame_bytes))

        # TODO: Phase 4 — call video_analysis.py, update mastery, /update agent
        return JsonResponse({"analyzed": False, "visual_state": {"confidence": "medium", "emotion": "neutral"}})


class VoiceSessionContextView(View):
    """GET /api/v1/voice-sessions/{session_id}/context/ — Debug: inspect current prompt + mastery."""

    async def get(self, request, session_id: str):  # type: ignore[override]
        session = await get_session(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        mastery: MasteryState = session["mastery"]
        context = reconstruct_context(session["context_args"])

        # Build the current prompt (what would be sent to /update)
        current_prompt = context.build_enriched_prompt(mastery)

        result = {
            "session_id": session_id,
            "agent_id": session["agent_id"],
            "agent_alive": session.get("agent_alive", True),
            "mastery": mastery.model_dump(),
            "current_system_prompt": current_prompt,
            "prompt_length": len(current_prompt),
        }

        # Try to get conversation history from ConvoAI
        if session.get("agent_alive", True):
            try:
                client = get_client()
                history = await client.get_history(session["agent_id"])
                result["conversation_history"] = history
            except Exception as e:
                result["conversation_history_error"] = str(e)

        return JsonResponse(result, json_dumps_params={"indent": 2, "ensure_ascii": False})


class VoiceSessionBiomarkersView(View):
    """POST /api/v1/voice-sessions/{session_id}/biomarkers/ — Receive Thymia scores."""

    async def post(self, request, session_id: str):  # type: ignore[override]
        session = await get_session(session_id)
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        if not session.get("agent_alive", True):
            return JsonResponse({"error": "Agent is no longer active"}, status=409)

        try:
            body = json.loads(request.body)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

        from services.convoai.schemas import BiomarkerState

        # Update mastery with new biomarker scores
        mastery: MasteryState = session["mastery"]
        mastery.biomarkers = BiomarkerState(
            stress=float(body.get("stress", 0.0)),
            exhaustion=float(body.get("exhaustion", 0.0)),
            distress=float(body.get("distress", 0.0)),
        )

        from services.convoai.session_store import update_mastery

        await update_mastery(session_id, mastery)

        # Refresh agent context with biomarker data
        context = reconstruct_context(session["context_args"])
        enriched_prompt = context.build_enriched_prompt(mastery)

        client = get_client()
        try:
            await client.update_agent(session["agent_id"], enriched_prompt)
        except Exception as e:
            logger.warning("Failed to update agent with biomarkers: %s", e)
            return JsonResponse({"error": f"Agent update failed: {e}"}, status=502)

        return JsonResponse({"updated": True, "biomarkers": mastery.biomarkers.model_dump()})


def reconstruct_context(context_args: dict) -> VoicePracticeContext:
    """Reconstruct VoicePracticeContext from stored constructor args."""
    level_raw = context_args.get("level_summary")
    return VoicePracticeContext(
        student_name=context_args["student_name"],
        student_level=context_args["student_level"],
        language_pair=LanguagePair.model_validate(context_args["language_pair"]),
        errors=[ErrorDetail.model_validate(e) for e in context_args["errors"]],
        themes=[ThemeDetail.model_validate(t) for t in context_args["themes"]],
        questions=[QuizQuestionSummary.model_validate(q) for q in context_args.get("questions", [])],
        level_summary=LevelSummary.model_validate(level_raw) if level_raw else None,
        raw_lesson_context=context_args.get("raw_lesson_context", ""),
    )


# --- Data loading ---


async def _load_lesson_context(student_id: str, lesson_id: str) -> dict:
    """Load lesson context from DB or return seeded demo data.

    Returns dict with keys: student_name, student_level, language_pair,
    errors, themes, questions, level_summary.
    """
    # Try loading from DB first
    try:
        from apps.accounts.models import Student
        from apps.learning_progress.models import ErrorPattern, LessonLevelAssessment
        from apps.skill_results.models import (
            ErrorRecord,
            LessonTheme,
            SkillExecution,
            SkillName,
        )
        from apps.tutoring.models import TutoringRelationship

        student = await Student.objects.aget(id=student_id)
        student_name = student.name

        # Get tutoring relationship for level/language
        relationship = await TutoringRelationship.objects.filter(student_id=student_id, status="active").afirst()

        if relationship:
            student_level = relationship.current_level or "B1"
            config = relationship.subject_config or {}
            language_pair = LanguagePair(
                l1=config.get("l1", "Spanish"),
                l2=config.get("l2", "English"),
            )
        else:
            student_level = "B1"
            language_pair = LanguagePair(l1="Spanish", l2="English")

        # Build lookup maps for enrichment
        pattern_map: dict[tuple[str, str], ErrorPattern] = {}
        async for p in ErrorPattern.objects.filter(student_id=student_id):
            pattern_map[(p.error_type, p.error_subtype)] = p

        record_map: dict[tuple[str, str], ErrorRecord] = {}
        async for r in ErrorRecord.objects.filter(lesson_id=lesson_id):
            record_map[(r.error_type, r.error_subtype)] = r

        # Load errors from skill execution
        errors: list[ErrorDetail] = []
        error_execution = await SkillExecution.objects.filter(
            lesson_id=lesson_id, skill_name=SkillName.ANALYZE_ERRORS, status="completed"
        ).afirst()
        if error_execution and error_execution.output_data:
            for err in error_execution.output_data.get("errors", []):
                etype = err.get("type", "grammar")
                esub = err.get("subtype", err.get("type", "unknown"))
                record = record_map.get((etype, esub))
                pattern = pattern_map.get((etype, esub))
                errors.append(
                    ErrorDetail(
                        error_type=etype,
                        subtype=esub,
                        severity=err.get("severity", "moderate"),
                        original=err.get("original", ""),
                        corrected=err.get("corrected", ""),
                        explanation=err.get("explanation", ""),
                        l1_transfer=record.l1_transfer if record else err.get("l1_transfer", False),
                        l1_transfer_explanation=(
                            record.l1_transfer_explanation if record else err.get("l1_transfer_explanation", "")
                        ),
                        pattern_status=pattern.status if pattern else "",
                    )
                )

        # Load themes from parsed LessonTheme rows (richer than raw output_data)
        themes: list[ThemeDetail] = []
        has_theme_rows = False
        async for lt in LessonTheme.objects.filter(lesson_id=lesson_id):
            has_theme_rows = True
            active = _extract_vocab_terms(lt.vocabulary_active, limit=5)
            passive = _extract_vocab_terms(lt.vocabulary_passive, limit=3)
            themes.append(
                ThemeDetail(
                    topic=lt.topic,
                    vocabulary=active,
                    communicative_function=lt.communicative_function,
                    vocabulary_active=active,
                    vocabulary_passive=passive,
                    chunks=lt.chunks[:4] if lt.chunks else [],
                )
            )

        # Fallback to skill execution output if no parsed rows
        if not has_theme_rows:
            theme_execution = await SkillExecution.objects.filter(
                lesson_id=lesson_id, skill_name=SkillName.ANALYZE_THEMES, status="completed"
            ).afirst()
            if theme_execution and theme_execution.output_data:
                for th in theme_execution.output_data.get("themes", []):
                    themes.append(
                        ThemeDetail(
                            topic=th.get("topic", ""),
                            vocabulary=th.get("vocabulary", []),
                        )
                    )

        # Load quiz questions
        questions: list[QuizQuestionSummary] = []
        q_execution = await SkillExecution.objects.filter(
            lesson_id=lesson_id, skill_name=SkillName.GENERATE_QUESTIONS, status="completed"
        ).afirst()
        if q_execution and q_execution.output_data:
            for i, q in enumerate(q_execution.output_data.get("questions", [])):
                payload = q.get("payload", {})
                source_ref = q.get("source_ref", {})
                questions.append(
                    QuizQuestionSummary(
                        index=i,
                        question_type=q.get("payload_type", ""),
                        title=payload.get("title", q.get("title", "")),
                        error_subtype=source_ref.get("subtype", ""),
                        error_type=source_ref.get("error_type", ""),
                    )
                )

        # Load level assessment
        level_summary: LevelSummary | None = None
        level_assessment = await LessonLevelAssessment.objects.filter(
            lesson_id=lesson_id,
        ).afirst()
        if level_assessment:
            level_summary = LevelSummary(
                overall_level=level_assessment.overall_level,
                accuracy_level=level_assessment.accuracy_level,
                fluency_level=level_assessment.fluency_level,
                strengths=level_assessment.strengths[:3] if level_assessment.strengths else [],
                gaps=level_assessment.gaps[:4] if level_assessment.gaps else [],
            )

        return {
            "student_name": student_name,
            "student_level": student_level,
            "language_pair": language_pair,
            "errors": errors,
            "themes": themes[:4],
            "questions": questions,
            "level_summary": level_summary,
        }

    except Student.DoesNotExist:
        logger.info("Student %s not in DB, using seeded demo data", student_id)
    except ImportError:
        logger.info("DB models not available, using seeded demo data")
    except Exception:
        logger.warning(
            "Unexpected error loading lesson context for student=%s lesson=%s, falling back to demo data",
            student_id,
            lesson_id,
            exc_info=True,
        )

    # Try loading from data files (hackathon lesson analysis output)
    file_data = _load_from_data_files(lesson_id)
    if file_data:
        return file_data

    # Last resort: seeded demo data (Maria, B1, Spanish->English)
    return _seeded_demo_data()


def _extract_vocab_terms(vocab_list: list, limit: int = 5) -> list[str]:
    """Extract plain terms from vocabulary list (may be dicts or strings)."""
    terms = []
    for v in vocab_list[:limit]:
        if isinstance(v, dict):
            terms.append(v.get("term", str(v)))
        else:
            terms.append(str(v))
    return terms


def _load_questions_data(lesson_id: str) -> dict[str, dict]:
    """Load question→error mapping from data/ files.

    Returns a dict keyed by question index (as string) with error metadata.
    The quiz bridge uses this to map Classtime question_ids to error subtypes
    when Pusher events arrive.

    Format: {"0": {"error_subtype": "preposition_governance", "error_index": 1, ...}, ...}
    """
    import json


    data_root = Path(settings.BASE_DIR).parent / "data"
    if not data_root.exists():
        return {}

    lesson_dir = _find_lesson_dir(data_root, lesson_id)
    if not lesson_dir:
        return {}

    # Try questions.json first (emu-* format)
    questions_file = lesson_dir / "questions.json"
    if questions_file.exists():
        try:
            with open(questions_file) as f:
                data = json.load(f)
            questions = data.get("questions", [])
            result: dict[str, dict] = {}
            for i, q in enumerate(questions):
                ref = q.get("source_ref", {})
                result[str(i)] = {
                    "error_subtype": ref.get("subtype", "unknown"),
                    "error_type": ref.get("error_type", "grammar"),
                    "error_index": ref.get("error_index", i),
                    "original": ref.get("original", ""),
                    "corrected": ref.get("corrected", ""),
                    "severity": ref.get("severity", "moderate"),
                }
            logger.info("Loaded %d question→error mappings from %s", len(result), questions_file)
            return result
        except Exception:
            logger.warning("Could not load questions.json", exc_info=True)

    # Fallback: parse questions.md (exp-* format from generate-classtime-questions skill)
    questions_md = lesson_dir / "questions.md"
    if questions_md.exists():
        try:
            return _parse_questions_md(questions_md)
        except Exception:
            logger.warning("Could not parse questions.md", exc_info=True)

    logger.warning("No questions.json or questions.md found in %s", lesson_dir)
    return {}


def _load_raw_lesson_context(lesson_id: str) -> str:
    """Load raw markdown from lesson analysis files for full context injection.

    Concatenates errors, themes, and level analysis files into a single string.
    """


    data_root = Path(settings.BASE_DIR).parent / "data"
    if not data_root.exists():
        return ""

    lesson_dir = _find_lesson_dir(data_root, lesson_id)
    if not lesson_dir:
        return ""

    def _read_and_strip_frontmatter(filepath: object) -> str:
        content = filepath.read_text()  # type: ignore[union-attr]
        if content.startswith("---"):
            try:
                end = content.index("---", 3)
                content = content[end + 3:].strip()
            except ValueError:
                pass
        return content

    # Load files in priority order (errors most important, then level, then themes)
    parts = []
    budget = 10000  # ~2500 tokens — safe for Agora ConvoAI proxy
    used = 0

    for filename in ("analyze-lesson-errors.md", "analyze-lesson-level.md", "analyze-lesson-themes.md"):
        filepath = lesson_dir / filename
        if filepath.exists():
            content = _read_and_strip_frontmatter(filepath)
            if used + len(content) > budget:
                remaining = budget - used
                if remaining > 500:
                    # Truncate at last complete section (### boundary)
                    truncated = content[:remaining]
                    last_section = truncated.rfind("\n### ")
                    if last_section > 0:
                        truncated = truncated[:last_section]
                    parts.append(truncated + "\n\n[... remaining content omitted for voice agent ...]")
                    used += len(truncated)
                break
            parts.append(content)
            used += len(content)

    raw = "\n\n---\n\n".join(parts)
    logger.info("[SESSION_START] Loaded raw lesson context: %d chars from %s", len(raw), lesson_dir)
    return raw


def _parse_questions_md(questions_md: object) -> dict[str, dict]:
    """Parse questions.md (markdown format from generate-classtime-questions skill).

    Extracts question→error mapping from ### Q{n} sections by reading
    **Pattern:** and **Source error:** lines.
    """
    import re

    content = questions_md.read_text()  # type: ignore[union-attr]
    result: dict[str, dict] = {}

    # Split into question sections: ### Q1: fill_in_blank | zpd_target | production
    sections = re.split(r"### Q(\d+):", content)
    # sections[0] is preamble, then alternating: number, content
    for i in range(1, len(sections) - 1, 2):
        q_num = sections[i].strip()
        q_content = sections[i + 1]
        q_index = str(int(q_num) - 1)  # Q1 -> "0", Q2 -> "1"

        # Extract pattern
        pattern_match = re.search(r"\*\*Pattern:\*\*\s*(.+)", q_content)
        pattern = pattern_match.group(1).strip() if pattern_match else "unknown"

        # Extract source error: #4 - "text" (grammar/case_declension, ...)
        source_match = re.search(
            r"\*\*Source error:\*\*\s*#(\d+)\s*-\s*\"(.+?)\"\s*\((\w+)/(\w+)",
            q_content,
        )
        if source_match:
            error_index = int(source_match.group(1))
            original = source_match.group(2)
            error_type = source_match.group(3)
            subtype = source_match.group(4)
        else:
            error_index = int(q_num) - 1
            original = ""
            error_type = "grammar"
            subtype = pattern

        # Extract correct answer
        correct_match = re.search(r"\*\*Correct answer:\*\*\s*(.+)", q_content)
        corrected = correct_match.group(1).strip() if correct_match else ""

        result[q_index] = {
            "error_subtype": subtype,
            "error_type": error_type,
            "error_index": error_index,
            "original": original,
            "corrected": corrected,
            "severity": "moderate",
            "pattern": pattern,
        }

    logger.info("Parsed %d question→error mappings from %s", len(result), questions_md)
    return result


_LANG_CODES = {"de": "German", "en": "English", "es": "Spanish", "uk": "Ukrainian", "pl": "Polish"}


def _load_from_data_files(lesson_id: str) -> dict | None:
    """Load lesson context from data/ markdown files (hackathon analysis output).

    Supports two directory layouts:
      data/{lesson_id}/analyze-lesson-errors.md          (emu-* dirs)
      data/{lesson_id}/{lesson_id}/analyze-lesson-errors.md  (exp-* dirs with nesting)

    Language pair is resolved from:
      1. frontmatter `language_pair: Ukrainian -> Polish`
      2. dir name pattern `emu-{l1}-{l2}-{level}-{number}`
    """


    data_root = Path(settings.BASE_DIR).parent / "data"
    if not data_root.exists():
        return None

    # 1. Find the lesson directory by lesson_id
    lesson_dir = _find_lesson_dir(data_root, lesson_id)
    if not lesson_dir:
        return None

    errors_file = lesson_dir / "analyze-lesson-errors.md"
    themes_file = lesson_dir / "analyze-lesson-themes.md"
    level_file = lesson_dir / "analyze-lesson-level.md"

    if not errors_file.exists():
        return None

    logger.info("Loading lesson context from %s", lesson_dir)

    # 2. Parse metadata from frontmatter
    errors_content = errors_file.read_text()
    fm = _parse_frontmatter(errors_content)

    raw_student = fm.get("student_id", "Student").replace('"', "")
    # Extract first name only: "vasyl-student" -> "Vasyl", "student-oksana" -> "Oksana"
    parts = [p for p in raw_student.split("-") if p.lower() != "student"]
    student_name = parts[0].title() if parts else raw_student.title()

    # Level: prefer level file, fallback to errors frontmatter
    student_level = fm.get("estimated_level", "B1")
    if level_file.exists():
        level_fm = _parse_frontmatter(level_file.read_text())
        student_level = level_fm.get("level", student_level)
    student_level = student_level.strip('"')

    # Language pair: frontmatter > dir name > default
    l1, l2 = _resolve_language_pair(fm, lesson_dir.name)

    # 3. Parse errors (priority: major > moderate > minor, limit 8)
    errors = _parse_errors_from_md(errors_content, max_errors=8)

    # 4. Parse themes
    themes: list[ThemeDetail] = []
    if themes_file.exists():
        themes = _parse_themes_from_md(themes_file.read_text(), max_themes=4)

    # 5. Load questions from questions.json if available
    questions = _load_questions_summaries_from_file(lesson_dir)

    logger.info(
        "Loaded from files: student=%s level=%s lang=%s->%s errors=%d themes=%d questions=%d",
        student_name, student_level, l1, l2, len(errors), len(themes), len(questions),
    )
    return {
        "student_name": student_name,
        "student_level": student_level,
        "language_pair": LanguagePair(l1=l1, l2=l2),
        "errors": errors,
        "themes": themes,
        "questions": questions,
        "level_summary": None,
    }


def _find_lesson_dir(data_root: "Path", lesson_id: str) -> "Path | None":
    """Find the directory containing lesson analysis files."""


    # Direct match: data/{lesson_id}/
    candidate = data_root / lesson_id
    if candidate.is_dir() and (candidate / "analyze-lesson-errors.md").exists():
        return candidate

    # Nested match: data/{lesson_id}/{lesson_id}/ (exp-* layout)
    nested = candidate / lesson_id
    if nested.is_dir() and (nested / "analyze-lesson-errors.md").exists():
        return nested

    # Also check storage subdirs: data/{lesson_id}/storage/lessons/{lesson_id}/
    storage = candidate / "storage" / "lessons" / lesson_id
    if storage.is_dir() and (storage / "analyze-lesson-errors.md").exists():
        return storage

    # Scan all dirs for matching lesson_id in frontmatter
    for path in data_root.rglob("analyze-lesson-errors.md"):
        content = path.read_text(errors="replace")[:500]
        if f"lesson_id: {lesson_id}" in content or f'lesson_id: "{lesson_id}"' in content:
            return path.parent

    return None


def _resolve_language_pair(fm: dict[str, str], dir_name: str) -> tuple[str, str]:
    """Resolve L1→L2 from frontmatter or directory name."""
    # Frontmatter: language_pair: Ukrainian -> Polish
    lp = fm.get("language_pair", "")
    if "->" in lp:
        parts = lp.split("->")
        return parts[0].strip().strip('"'), parts[1].strip().strip('"')

    # Dir name pattern: emu-{l1}-{l2}-{level}-{number}
    parts = dir_name.split("-")
    if len(parts) >= 3 and parts[0] == "emu":
        l1 = _LANG_CODES.get(parts[1], parts[1].title())
        l2 = _LANG_CODES.get(parts[2], parts[2].title())
        return l1, l2

    return "Ukrainian", "English"


def _parse_errors_from_md(content: str, max_errors: int = 8) -> list[ErrorDetail]:
    """Parse errors from analyze-lesson-errors.md, prioritizing by severity."""
    import re

    errors: list[ErrorDetail] = []
    error_pattern = re.compile(
        r"### #\d+ (\w+)/(\w+) \((\w+)\).*?\n\n"
        r"\*\*Original:\*\* (.+?)\n"
        r"\*\*Corrected:\*\* (.+?)\n\n"
        r"(.+?)(?=\n### #|\n## )",
        re.DOTALL,
    )
    for match in error_pattern.finditer(content):
        error_type, subtype, severity = match.group(1), match.group(2), match.group(3)
        original, corrected = match.group(4).strip(), match.group(5).strip()
        explanation = match.group(6).strip().split("\n")[0]
        errors.append(ErrorDetail(
            error_type=error_type,
            subtype=subtype,
            severity=severity,
            original=original,
            corrected=corrected,
            explanation=explanation,
        ))

    # Prioritize: major > moderate > minor
    severity_order = {"major": 0, "moderate": 1, "minor": 2}
    errors.sort(key=lambda e: severity_order.get(e.severity, 3))
    return errors[:max_errors]


def _parse_themes_from_md(content: str, max_themes: int = 4) -> list[ThemeDetail]:
    """Parse themes from analyze-lesson-themes.md."""
    import re

    themes: list[ThemeDetail] = []
    vocab_pattern = re.compile(r"\| ([\w\s/àáâãäåæçèéêëìíîïðñòóôõöùúûüýþÿąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+?) \|")
    sections = content.split("### ")[1:]
    for section in sections[:max_themes]:
        title_match = re.match(r"\d+\. (.+?) \[", section)
        if title_match:
            topic = title_match.group(1).strip()
            vocab = [m.group(1).strip() for m in vocab_pattern.finditer(section)][:6]
            themes.append(ThemeDetail(topic=topic, vocabulary=vocab))
    return themes


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Parse YAML-like frontmatter from markdown file."""
    if not content.startswith("---"):
        return {}
    try:
        end = content.index("---", 3)
    except ValueError:
        return {}
    fm_text = content[3:end]
    result: dict[str, str] = {}
    for line in fm_text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip().strip('"')
    return result


def _load_questions_summaries_from_file(lesson_dir: "Path") -> list[QuizQuestionSummary]:
    """Load quiz question summaries from questions.json in lesson data dir."""
    questions_file = lesson_dir / "questions.json"
    if not questions_file.exists():
        return []
    try:
        with open(questions_file) as f:
            data = json.load(f)
        summaries = []
        for i, q in enumerate(data.get("questions", [])):
            payload = q.get("payload", {})
            source_ref = q.get("source_ref", {})
            summaries.append(
                QuizQuestionSummary(
                    index=i,
                    question_type=q.get("payload_type", ""),
                    title=payload.get("title", q.get("title", "")),
                    error_subtype=source_ref.get("subtype", ""),
                    error_type=source_ref.get("error_type", ""),
                )
            )
        return summaries
    except Exception:
        logger.warning("Could not load question summaries from %s", questions_file, exc_info=True)
        return []


def _seeded_demo_data() -> dict:
    """Demo data for hackathon: Maria, B1 Spanish->English student."""
    return {
        "student_name": "Maria",
        "student_level": "B1",
        "language_pair": LanguagePair(l1="Spanish", l2="English"),
        "errors": [
            ErrorDetail(
                error_type="grammar",
                subtype="articles",
                severity="major",
                original="I go to the school every day",
                corrected="I go to school every day",
                explanation="No article before 'school' when referring to the activity/institution",
                l1_transfer=True,
                l1_transfer_explanation="In Spanish, articles are used before institutions (la escuela)",
            ),
            ErrorDetail(
                error_type="grammar",
                subtype="past_tense_irregular",
                severity="moderate",
                original="Yesterday I goed to the cinema",
                corrected="Yesterday I went to the cinema",
                explanation="'go' is irregular: go -> went -> gone",
            ),
            ErrorDetail(
                error_type="grammar",
                subtype="third_person_singular",
                severity="major",
                original="She don't like coffee",
                corrected="She doesn't like coffee",
                explanation="Third person singular uses 'doesn't' (does + not)",
            ),
            ErrorDetail(
                error_type="grammar",
                subtype="prepositions",
                severity="minor",
                original="I'm good in math",
                corrected="I'm good at math",
                explanation="'good at' is the correct collocation, not 'good in'",
                l1_transfer=True,
                l1_transfer_explanation="Spanish uses 'bueno en' (good in), English uses 'good at'",
            ),
        ],
        "themes": [
            ThemeDetail(topic="Morning routine", vocabulary=["wake up", "commute", "breakfast", "schedule"]),
            ThemeDetail(topic="Travel planning", vocabulary=["destination", "booking", "itinerary", "passport"]),
        ],
        "questions": [],
        "level_summary": None,
    }
