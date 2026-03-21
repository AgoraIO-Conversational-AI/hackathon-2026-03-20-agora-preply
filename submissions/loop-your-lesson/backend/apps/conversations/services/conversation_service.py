"""Conversation service functions."""

from apps.accounts.models import Student, Teacher
from apps.conversations.models import Conversation, ConversationStatus
from apps.lessons.models import LessonStudent
from apps.tutoring.models import TutoringRelationship


def resolve_conversation_context(mode, teacher_id=None, student_id=None, lesson_id=None):
    """Auto-resolve missing context based on mode. Returns (teacher_id, student_id, lesson_id)."""
    if not teacher_id:
        teacher = Teacher.objects.first()
        teacher_id = str(teacher.id) if teacher else None

    if mode == "student_practice" and not student_id:
        student = Student.objects.first()
        student_id = str(student.id) if student else None

    if mode == "student_practice" and not lesson_id and student_id:
        ls = (
            LessonStudent.objects.filter(student_id=student_id)
            .select_related("lesson")
            .order_by("-lesson__date")
            .first()
        )
        lesson_id = str(ls.lesson_id) if ls else None

    # Resolve teacher from tutoring relationship if still missing
    if not teacher_id and student_id:
        rel = TutoringRelationship.objects.filter(student_id=student_id).first()
        if rel:
            teacher_id = str(rel.teacher_id)

    return teacher_id, student_id, lesson_id


def get_or_create_conversation(conversation_id, mode, teacher_id=None, student_id=None, lesson_id=None):
    """Get existing or create new conversation with context."""
    if Conversation.objects.filter(id=conversation_id).exists():
        return Conversation.objects.get(id=conversation_id)

    return Conversation.objects.create(
        id=conversation_id,
        mode=mode,
        status=ConversationStatus.ACTIVE,
        teacher_id=teacher_id,
        student_id=student_id,
        lesson_id=lesson_id,
    )


def format_conversation_messages(conversation):
    """Format conversation messages for frontend display.

    Returns list of message dicts with toolResults and processSteps.
    Adapted from Medallion conversation_detail_view pattern.
    """
    frontend_messages = []
    messages = (
        conversation.messages.filter(role__in=["user", "assistant"])
        .prefetch_related("tool_executions")
        .order_by("created_at")
    )

    for msg in messages:
        entry = {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content or "",
            "timestamp": msg.created_at.isoformat(),
        }

        # Build executions_by_id once per message (avoids duplicate query)
        executions_by_id = {}
        if msg.role == "assistant" and msg.tool_calls:
            executions_by_id = {te.tool_use_id: te for te in msg.tool_executions.all()}
            tool_results = []
            for tc in msg.tool_calls:
                te = executions_by_id.get(tc.get("id", ""))
                if te:
                    tool_results.append(
                        {
                            "toolName": te.tool_name,
                            "toolId": te.tool_use_id,
                            "toolInput": te.input_args or {},
                            "message": te.result_message,
                            "data": te.result_data or {},
                            "executionTimeMs": te.execution_time_ms,
                            "success": te.success,
                        }
                    )
                else:
                    tool_results.append(
                        {
                            "toolName": tc.get("name", ""),
                            "toolId": tc.get("id", ""),
                            "toolInput": tc.get("input", {}),
                            "message": "",
                            "data": {},
                        }
                    )
            if tool_results:
                entry["toolResults"] = tool_results

        # processSteps come exclusively from metadata.process_steps (the
        # authoritative timeline accumulated by the agent loop). We never
        # synthesize from tool_calls — that would duplicate entries when the
        # frontend merges consecutive assistant messages.
        if msg.role == "assistant":
            metadata = msg.metadata or {}
            if metadata.get("process_steps"):
                entry["processSteps"] = metadata["process_steps"]

        frontend_messages.append(entry)

    return frontend_messages
