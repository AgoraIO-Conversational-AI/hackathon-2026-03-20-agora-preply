from collections import Counter

from asgiref.sync import sync_to_async
from pydantic import BaseModel

from apps.classtime_sessions.models import ClasstimeSession, PracticeQuestion
from apps.classtime_sessions.services.sessions import create_practice_for_lesson
from apps.conversations.services.tools import PreplyTool, register_tool
from apps.skill_results.models import SkillExecution, SkillExecutionStatus, SkillName


class CreatePracticeSessionArgs(BaseModel):
    pass


@sync_to_async
def _get_or_create_session(lesson_id, student_id, teacher_id):
    """Check for existing session or create one from skill output."""
    from apps.accounts.models import Student, Teacher
    from apps.lessons.models import Lesson

    lesson = Lesson.objects.filter(id=lesson_id).first()
    if not lesson:
        return None, "Lesson not found."

    # Check if a session with a student URL already exists for this lesson
    existing = (
        ClasstimeSession.objects.filter(lesson=lesson)
        .exclude(student_url="")
        .order_by("-created_at")
        .first()
    )
    if existing:
        return existing, None

    # Find completed generate-classtime-questions skill execution
    execution = (
        SkillExecution.objects.filter(
            lesson=lesson,
            skill_name=SkillName.GENERATE_QUESTIONS,
            status=SkillExecutionStatus.COMPLETED,
        )
        .order_by("-completed_at")
        .first()
    )

    if not execution or not execution.output_data.get("questions"):
        return None, "No practice questions available yet. The lesson needs to be analyzed first."

    teacher = Teacher.objects.filter(id=teacher_id).first() if teacher_id else lesson.teacher
    student = Student.objects.filter(id=student_id).first() if student_id else None

    if not teacher:
        return None, "Teacher not found."
    if not student:
        return None, "Student not found."

    session = create_practice_for_lesson(teacher, student, execution.output_data, lesson)
    return session, None


@sync_to_async
def _build_practice_card(session):
    """Build practice_card widget data from a ClasstimeSession."""
    questions = (
        PracticeQuestion.objects.filter(session=session)
        .select_related("error_record")
        .order_by("question_index")
    )

    question_types = dict(Counter(q.question_type for q in questions))

    source_errors = []
    for q in questions:
        if q.error_record:
            source_errors.append({
                "timestamp": q.error_record.timestamp,
                "original": q.error_record.original_text,
                "corrected": q.error_record.corrected_text,
            })

    # Get focus topic from skill output or session title
    focus_topic = "Lesson errors"
    if session.question_skill_execution and session.question_skill_execution.output_data:
        focus_topic = session.question_skill_execution.output_data.get("session_title", focus_topic)

    # Get themes from lesson themes
    themes = []
    if session.lesson:
        from apps.skill_results.models import LessonTheme

        themes = list(
            LessonTheme.objects.filter(lesson=session.lesson).values_list("topic", flat=True)
        )

    return {
        "widget_type": "practice_card",
        "question_count": len(questions),
        "question_types": question_types,
        "focus_topic": focus_topic,
        "source_errors": source_errors,
        "themes": themes,
        "session_url": session.student_url,
        "session_code": session.session_code,
        "student_id": str(session.student_id) if session.student_id else None,
        "lesson_id": str(session.lesson_id) if session.lesson_id else None,
        "student_name": session.student.name if session.student else None,
    }


@register_tool
class CreatePracticeSessionTool(PreplyTool):
    @property
    def name(self):
        return "create_practice_session"

    @property
    def description(self):
        return (
            "Create a practice session from lesson analysis. "
            "Returns a practice card with a 'Start practice' button. "
            "If a session already exists, returns the existing one."
        )

    @property
    def args_schema(self):
        return CreatePracticeSessionArgs

    @property
    def category(self):
        return "action"

    async def execute(self, *, conversation=None):
        if not conversation or not conversation.lesson_id:
            return "No lesson context available. Cannot create a practice session.", {}

        session, error = await _get_or_create_session(
            conversation.lesson_id,
            conversation.student_id,
            getattr(conversation, "teacher_id", None),
        )

        if error:
            return error, {}

        data = await _build_practice_card(session)

        message = (
            f"Practice session ready with {data['question_count']} exercises. "
            "Click 'Start practice' to begin."
        )
        return message, data
