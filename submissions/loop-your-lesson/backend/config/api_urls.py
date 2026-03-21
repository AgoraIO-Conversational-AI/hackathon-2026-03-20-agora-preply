"""API URL configuration with real implementations."""

import asyncio
import json
import uuid
from datetime import date

from django.http import JsonResponse, StreamingHttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.accounts.models import Student, Teacher
from apps.classtime_sessions.models import ClasstimeSession, PracticeQuestion, PracticeResult, SessionParticipant
from apps.classtime_sessions.services.results import sync_session_results
from apps.classtime_sessions.services.sessions import create_practice_for_lesson
from apps.conversations.models import Conversation, ConversationManager
from apps.conversations.services.conversation_service import (
    format_conversation_messages,
    get_or_create_conversation,
    resolve_conversation_context,
)
from apps.learning_progress.models import (
    ErrorPattern,
    ErrorPatternOccurrence,
    ErrorPatternStatus,
    LessonLevelAssessment,
)
from apps.lessons.models import Lesson, LessonStudent
from apps.skill_results.models import ErrorRecord, LessonTheme, SkillExecution
from apps.tutoring.models import TutoringRelationship, TutoringStatus
from services.convoai.views import (
    VoiceSessionBiomarkersView,
    VoiceSessionContextView,
    VoiceSessionFrameView,
    VoiceSessionStartView,
    VoiceSessionStatusView,
    VoiceSessionStopView,
)
from services.temporal_client import get_temporal_client
from stream.redis_stream import get_redis_connection, get_stream_key
from stream.sse import stream_conversation
from workflows.chat_agent import ChatAgentInput, ChatAgentWorkflow

# Voice session views (csrf_exempt for API calls)
voice_session_start = csrf_exempt(VoiceSessionStartView.as_view())
voice_session_status = VoiceSessionStatusView.as_view()
voice_session_stop = csrf_exempt(VoiceSessionStopView.as_view())
voice_session_frame = csrf_exempt(VoiceSessionFrameView.as_view())
voice_session_biomarkers = csrf_exempt(VoiceSessionBiomarkersView.as_view())
voice_session_context = VoiceSessionContextView.as_view()

TASK_QUEUE = "loop-your-lesson"
STREAM_TIMEOUT_SECONDS = 300


# --- Streaming infrastructure ---


def _read_redis_stream_sync(conversation_id: str, last_id: str = "0"):
    """Bridge async Redis reads to sync generator for StreamingHttpResponse."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        agen = stream_conversation(conversation_id, last_id=last_id, timeout_seconds=STREAM_TIMEOUT_SECONDS)
        while True:
            try:
                yield loop.run_until_complete(agen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


# --- Conversation endpoints ---


@csrf_exempt
@require_http_methods(["POST"])
def stream_conversation_view(request, conversation_id):
    """Stream a conversation response via SSE.

    POST /api/v1/conversations/<id>/stream/
    Body: {"message": "...", "mode": "daily_briefing"}

    Starts a Temporal workflow, returns SSE stream from Redis.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = body.get("message")
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    mode = body.get("mode", "daily_briefing")

    teacher_id, student_id, lesson_id = resolve_conversation_context(
        mode,
        body.get("teacher_id"),
        body.get("student_id"),
        body.get("lesson_id"),
    )
    get_or_create_conversation(conversation_id, mode, teacher_id, student_id, lesson_id)

    # Single event loop for all async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Clear stale Redis stream
        try:
            redis = loop.run_until_complete(get_redis_connection())
            loop.run_until_complete(redis.delete(get_stream_key(str(conversation_id))))
            loop.run_until_complete(redis.close())
        except Exception:
            pass

        # Start Temporal workflow
        client = loop.run_until_complete(get_temporal_client())
        turn_id = str(uuid.uuid4())[:8]
        loop.run_until_complete(
            client.start_workflow(
                ChatAgentWorkflow.run,
                ChatAgentInput(
                    conversation_id=str(conversation_id),
                    message=message,
                    mode=mode,
                    teacher_id=teacher_id,
                    student_id=student_id,
                    lesson_id=lesson_id,
                ),
                id=f"chat-{conversation_id}-{turn_id}",
                task_queue=TASK_QUEUE,
            )
        )
    finally:
        loop.close()

    # Return SSE stream reading from Redis
    response = StreamingHttpResponse(
        streaming_content=_read_redis_stream_sync(str(conversation_id)),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _conversation_context(c):
    """Build context dict for a conversation (teacher/student/lesson info)."""
    ctx = {}
    if c.teacher_id:
        ctx["teacher_id"] = str(c.teacher_id)
        ctx["teacher_name"] = c.teacher.name if c.teacher else None
    if c.student_id:
        ctx["student_id"] = str(c.student_id)
        ctx["student_name"] = c.student.name if c.student else None
        rel_filter = {"student_id": c.student_id}
        if c.teacher_id:
            rel_filter["teacher_id"] = c.teacher_id
        rel = TutoringRelationship.objects.filter(**rel_filter).first()
        if rel:
            ctx["student_level"] = rel.current_level
            ctx["student_goal"] = rel.goal
            ctx["total_lessons"] = rel.total_lessons
            ctx["subject_config"] = rel.subject_config
    if c.lesson_id:
        ctx["lesson_id"] = str(c.lesson_id)
        if c.lesson:
            ctx["lesson_date"] = str(c.lesson.date)
            ctx["lesson_summary"] = c.lesson.transcript_summary or ""
            ctx["lesson_duration"] = c.lesson.duration_minutes
    return ctx


@csrf_exempt
@require_http_methods(["GET"])
def list_conversations_view(request):
    """List recent conversations.

    GET /api/v1/conversations/list/
    """
    conversations = ConversationManager.get_recent_conversations()

    return JsonResponse(
        {
            "conversations": [
                {
                    "id": str(c.id),
                    "title": c.title or c.generate_title(),
                    "mode": c.mode,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                    **_conversation_context(c),
                }
                for c in conversations
            ]
        }
    )


@csrf_exempt
@require_http_methods(["GET"])
def get_conversation_view(request, conversation_id):
    """Get conversation with messages.

    GET /api/v1/conversations/<id>/
    """
    try:
        conversation = Conversation.objects.select_related(
            "teacher",
            "student",
            "lesson",
        ).get(id=conversation_id)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    return JsonResponse(
        {
            "id": str(conversation.id),
            "title": conversation.title or conversation.generate_title(),
            "mode": conversation.mode,
            "status": conversation.status,
            "messages": format_conversation_messages(conversation),
            **_conversation_context(conversation),
        }
    )


@csrf_exempt
@require_http_methods(["GET"])
def context_options_view(request):
    """Return available teachers, students, and lessons for context selection.

    GET /api/v1/context/
    """
    teachers = [{"id": str(t.id), "name": t.name} for t in Teacher.objects.all()[:20]]

    students_out = []
    for rel in TutoringRelationship.objects.filter(status="active").select_related("student"):
        student = rel.student
        lessons = []
        for ls in LessonStudent.objects.filter(student=student).select_related("lesson").order_by("-lesson__date")[:5]:
            lesson = ls.lesson
            lessons.append(
                {
                    "id": str(lesson.id),
                    "date": str(lesson.date),
                    "summary": lesson.transcript_summary or "",
                }
            )
        students_out.append(
            {
                "id": str(student.id),
                "name": student.name,
                "level": rel.current_level or "",
                "goal": rel.goal or "",
                "total_lessons": rel.total_lessons,
                "subject_config": rel.subject_config or {},
                "lessons": lessons,
            }
        )

    return JsonResponse({"teachers": teachers, "students": students_out})


# --- Placeholder endpoints (non-conversation) ---


@api_view(["GET"])
def teacher_tutoring(request, teacher_id):
    return Response([])


@api_view(["POST"])
def create_tutoring(request):
    return Response({})


@api_view(["PATCH"])
def update_tutoring(request, tutoring_id):
    return Response({})


@api_view(["POST"])
def create_lesson(request):
    return Response({})


@api_view(["POST"])
def add_lesson_students(request, lesson_id):
    return Response({})


@api_view(["GET"])
def lesson_transcript(request, lesson_id):
    return Response({})


@api_view(["GET"])
def lesson_skill_results(request, lesson_id):
    """Structured skill analysis for a lesson.

    GET /api/v1/lessons/<lesson_id>/skill-results/
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response({"error": f"Lesson {lesson_id} not found"}, status=404)

    # Errors with all meaningful fields
    errors = [
        {
            "type": r.error_type,
            "subtype": r.error_subtype,
            "severity": r.severity,
            "communicative_impact": r.communicative_impact,
            "original": r.original_text,
            "corrected": r.corrected_text,
            "explanation": r.explanation,
            "reasoning": r.reasoning,
            "l1_transfer": r.l1_transfer,
            "l1_transfer_explanation": r.l1_transfer_explanation,
            "correction_strategy": r.correction_strategy,
            "utterance_index": r.utterance_index,
            "timestamp": r.timestamp,
            "exercise_priority": r.exercise_priority,
        }
        for r in ErrorRecord.objects.filter(lesson=lesson).order_by("source_error_index")
    ]

    # Themes with initiated_by
    themes = [
        {
            "topic": t.topic,
            "communicative_function": t.communicative_function,
            "initiated_by": t.initiated_by,
            "vocabulary_active": t.vocabulary_active,
            "vocabulary_passive": t.vocabulary_passive,
            "chunks": t.chunks,
            "range": {"start": t.transcript_range_start, "end": t.transcript_range_end},
        }
        for t in LessonTheme.objects.filter(lesson=lesson)
    ]

    # Level assessment with suggestions
    assessment = LessonLevelAssessment.objects.filter(lesson=lesson).first()
    level = None
    if assessment:
        level = {
            "overall": assessment.overall_level,
            "dimensions": {
                "range": assessment.range_level,
                "accuracy": assessment.accuracy_level,
                "fluency": assessment.fluency_level,
                "interaction": assessment.interaction_level,
                "coherence": assessment.coherence_level,
            },
            "strengths": assessment.strengths,
            "gaps": assessment.gaps,
            "suggestions": assessment.suggestions,
            "zpd": {"lower": assessment.zpd_lower, "upper": assessment.zpd_upper},
        }

    # Error patterns linked to this lesson via ErrorPatternOccurrence
    pattern_occurrences = ErrorPatternOccurrence.objects.filter(
        lesson=lesson
    ).select_related("pattern")
    error_patterns = [
        {
            "label": occ.pattern.label,
            "error_type": occ.pattern.error_type,
            "error_subtype": occ.pattern.error_subtype,
            "status": occ.pattern.status,
            "occurrence_count": occ.pattern.occurrence_count,
            "lesson_count": occ.pattern.lesson_count,
            "times_tested": occ.pattern.times_tested,
            "times_correct": occ.pattern.times_correct,
            "mastery_score": occ.pattern.mastery_score,
        }
        for occ in pattern_occurrences
    ]

    # Classtime session with practice questions and results
    session = ClasstimeSession.objects.filter(lesson=lesson).first()
    classtime_session = None
    if session:
        questions = (
            PracticeQuestion.objects.filter(session=session)
            .select_related("error_record")
            .order_by("question_index")
        )
        participant = SessionParticipant.objects.filter(session=session).first()

        practice_questions = [
            {
                "question_index": q.question_index,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "stem": q.stem,
                "source_error": q.error_record.original_text if q.error_record else None,
            }
            for q in questions
        ]

        practice_results = []
        if participant:
            for result in PracticeResult.objects.filter(
                participant=participant
            ).select_related("practice_question"):
                practice_results.append({
                    "question_index": result.practice_question.question_index,
                    "is_correct": result.is_correct,
                    "student_answer": result.student_answer,
                })

        classtime_session = {
            "session_code": session.session_code,
            "student_url": session.student_url,
            "status": session.status,
            "questions": practice_questions,
            "results": practice_results,
            "completed": participant.completed_at is not None if participant else False,
        }

    # Skill execution status
    skill_status = {
        se.skill_name: se.status
        for se in SkillExecution.objects.filter(lesson=lesson)
    }

    return Response(
        {
            "lesson_id": str(lesson_id),
            "lesson_date": str(lesson.date),
            "errors": errors,
            "themes": themes,
            "level": level,
            "error_patterns": error_patterns,
            "classtime_session": classtime_session,
            "skill_status": skill_status,
        }
    )


@api_view(["POST"])
def create_skill_result(request):
    return Response({})


@api_view(["GET"])
def student_skill_results(request, student_id):
    """Cross-lesson progress for a student.

    GET /api/v1/students/<student_id>/skill-results/
    """
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": f"Student {student_id} not found"}, status=404)

    # Latest level
    assessment = LessonLevelAssessment.objects.filter(student=student).order_by("-created_at").first()
    latest_level = assessment.overall_level if assessment else ""

    # Error patterns
    patterns = [
        {
            "label": p.label,
            "pattern_key": p.pattern_key,
            "error_type": p.error_type,
            "status": p.status,
            "occurrence_count": p.occurrence_count,
            "lesson_count": p.lesson_count,
            "mastery_score": p.mastery_score,
            "times_tested": p.times_tested,
        }
        for p in ErrorPattern.objects.filter(student=student).order_by("-occurrence_count")
    ]

    # Recent assessments
    assessments = [
        {
            "lesson_date": str(a.lesson.date) if a.lesson else None,
            "level": a.overall_level,
            "strengths": a.strengths,
            "gaps": a.gaps,
        }
        for a in LessonLevelAssessment.objects.filter(student=student)
        .select_related("lesson")
        .order_by("-created_at")[:5]
    ]

    # Practice summary
    tested = ErrorPattern.objects.filter(student=student, times_tested__gt=0)
    mastered = tested.filter(status=ErrorPatternStatus.MASTERED).count()
    improving = tested.filter(status=ErrorPatternStatus.IMPROVING).count()

    return Response(
        {
            "student_id": str(student_id),
            "student_name": student.name,
            "latest_level": latest_level,
            "error_patterns": patterns,
            "recent_assessments": assessments,
            "practice_summary": {
                "total_tested": tested.count(),
                "mastered": mastered,
                "improving": improving,
            },
        }
    )


@api_view(["POST"])
def create_classtime_session(request):
    """Create a Classtime practice session from skill output.

    POST /api/v1/classtime-sessions/
    Body: {student_id, lesson_id, skill_output: {session_title, feedback_mode, questions[]}}
    """
    data = request.data
    student_id = data.get("student_id")
    lesson_id = data.get("lesson_id")
    skill_output = data.get("skill_output", {})

    if not student_id or not lesson_id or not skill_output.get("questions"):
        return Response({"error": "student_id, lesson_id, and skill_output with questions are required"}, status=400)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return Response({"error": f"Student {student_id} not found"}, status=404)

    try:
        lesson = Lesson.objects.get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response({"error": f"Lesson {lesson_id} not found"}, status=404)

    teacher = lesson.teacher
    session = create_practice_for_lesson(teacher, student, skill_output, lesson)

    return Response(
        {
            "id": str(session.id),
            "code": session.session_code,
            "question_set_id": session.question_set_id,
            "student_url": session.student_url,
            "questions_count": len(session.questions_data or []),
        }
    )


@api_view(["GET"])
def classtime_session_results(request, code):
    """Sync and return results for a Classtime session.

    GET /api/v1/classtime-sessions/<code>/results/
    """
    try:
        session = ClasstimeSession.objects.get(session_code=code)
    except ClasstimeSession.DoesNotExist:
        return Response({"error": f"Session {code} not found"}, status=404)

    results = sync_session_results(session)
    return Response(results)


@api_view(["GET"])
def classtime_session_participants(request, code):
    return Response([])


@api_view(["POST"])
def create_daily_briefing(request):
    return Response({})


@api_view(["GET"])
def get_daily_briefing(request, teacher_id):
    """Aggregated briefing data for all active students.

    GET /api/v1/daily-briefings/<teacher_id>/
    """
    try:
        teacher = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({"error": f"Teacher {teacher_id} not found"}, status=404)

    relationships = TutoringRelationship.objects.filter(
        teacher=teacher,
        status=TutoringStatus.ACTIVE,
    ).select_related("student")

    students = []
    for rel in relationships:
        student = rel.student

        # Latest lesson
        ls = (
            LessonStudent.objects.filter(student=student, lesson__teacher=teacher)
            .select_related("lesson")
            .order_by("-lesson__date")
            .first()
        )
        lesson = ls.lesson if ls else None

        # Error count from latest lesson
        error_count = ErrorRecord.objects.filter(lesson=lesson, student=student).count() if lesson else 0

        # Active error patterns
        active_patterns = [
            {
                "label": p.label,
                "status": p.status,
                "occurrence_count": p.occurrence_count,
                "lesson_count": p.lesson_count,
                "mastery_score": p.mastery_score,
            }
            for p in ErrorPattern.objects.filter(
                student=student,
                teacher=teacher,
                status__in=[ErrorPatternStatus.NEW, ErrorPatternStatus.RECURRING],
            ).order_by("-occurrence_count")[:5]
        ]

        # Practice results from latest session
        practice_results = None
        if lesson:
            session = ClasstimeSession.objects.filter(lesson=lesson).first()
            if session:
                participant = SessionParticipant.objects.filter(session=session, student=student).first()
                if participant and participant.results_data:
                    p_data = participant.results_data
                    practice_results = {
                        "score": p_data.get("score"),
                        "total": p_data.get("total"),
                        "percentage": p_data.get("percentage"),
                    }

        # Attention flags
        attention_flags = []
        for p in active_patterns:
            if p["lesson_count"] >= 3:
                attention_flags.append(f"{p['label']} - recurring across {p['lesson_count']} lessons")

        students.append(
            {
                "student_id": str(student.id),
                "name": student.name,
                "latest_level": rel.latest_level or rel.current_level or "",
                "last_lesson_date": str(lesson.date) if lesson else None,
                "error_count": error_count,
                "active_patterns": active_patterns,
                "mastered_patterns": rel.mastered_error_patterns,
                "practice_results": practice_results,
                "attention_flags": attention_flags,
            }
        )

    return Response(
        {
            "teacher_id": str(teacher_id),
            "date": str(date.today()),
            "students": students,
        }
    )


@api_view(["POST"])
def create_conversation(request):
    return Response({})


@api_view(["POST"])
def approve_tool(request, conversation_id):
    return Response({})


urlpatterns = [
    # Tutoring
    path("teachers/<str:teacher_id>/tutoring/", teacher_tutoring),
    path("tutoring/", create_tutoring),
    path("tutoring/<str:tutoring_id>/", update_tutoring),
    # Lessons
    path("lessons/", create_lesson),
    path("lessons/<str:lesson_id>/students/", add_lesson_students),
    path("lessons/<str:lesson_id>/transcript/", lesson_transcript),
    path("lessons/<str:lesson_id>/skill-results/", lesson_skill_results),
    # Skill results
    path("skill-results/", create_skill_result),
    path("students/<str:student_id>/skill-results/", student_skill_results),
    # Classtime sessions
    path("classtime-sessions/", create_classtime_session),
    path("classtime-sessions/<str:code>/results/", classtime_session_results),
    path("classtime-sessions/<str:code>/participants/", classtime_session_participants),
    # Daily briefings
    path("daily-briefings/", create_daily_briefing),
    path("daily-briefings/<str:teacher_id>/", get_daily_briefing),
    # Context
    path("context/", context_options_view),
    # Conversations
    path("conversations/", create_conversation),
    path("conversations/list/", list_conversations_view),
    path("conversations/<str:conversation_id>/", get_conversation_view),
    path("conversations/<str:conversation_id>/stream/", stream_conversation_view),
    path("conversations/<str:conversation_id>/approve/", approve_tool),
    # Voice practice sessions (Track 2)
    path("voice-sessions/", voice_session_start, name="voice-session-start"),
    path("voice-sessions/<str:session_id>/", voice_session_status, name="voice-session-status"),
    path("voice-sessions/<str:session_id>/stop/", voice_session_stop, name="voice-session-stop"),
    path("voice-sessions/<str:session_id>/frame/", voice_session_frame, name="voice-session-frame"),
    path("voice-sessions/<str:session_id>/biomarkers/", voice_session_biomarkers, name="voice-session-biomarkers"),
    path("voice-sessions/<str:session_id>/context/", voice_session_context, name="voice-session-context"),
]
