from datetime import date

from asgiref.sync import sync_to_async
from pydantic import BaseModel

from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant
from apps.conversations.services.tools import PreplyTool, register_tool
from apps.learning_progress.models import ErrorPattern, ErrorPatternStatus
from apps.lessons.models import LessonStudent
from apps.skill_results.models import ErrorRecord
from apps.tutoring.models import TutoringRelationship, TutoringStatus


class QueryDailyOverviewArgs(BaseModel):
    pass


@sync_to_async
def _fetch_daily_overview(teacher_id):
    relationships = list(
        TutoringRelationship.objects.filter(teacher_id=teacher_id, status=TutoringStatus.ACTIVE).select_related(
            "student"
        )
    )
    if not relationships:
        return None

    student_ids = [r.student_id for r in relationships]

    # Batch: most recent lesson per student
    recent_lessons = {}
    for ls in (
        LessonStudent.objects.filter(
            student_id__in=student_ids,
            lesson__teacher_id=teacher_id,
        )
        .select_related("lesson")
        .order_by("student_id", "-lesson__date")
    ):
        if ls.student_id not in recent_lessons:
            recent_lessons[ls.student_id] = ls.lesson

    lesson_ids = [lesson.id for lesson in recent_lessons.values()]

    # Batch: error counts from ErrorRecord (structured model)
    error_counts = {}
    for record in ErrorRecord.objects.filter(lesson_id__in=lesson_ids).values("lesson_id"):
        lid = record["lesson_id"]
        error_counts[lid] = error_counts.get(lid, 0) + 1

    # Batch: classtime sessions
    sessions_by_lesson = {}
    for session in ClasstimeSession.objects.filter(lesson_id__in=lesson_ids):
        sessions_by_lesson[session.lesson_id] = session

    # Batch: participants
    session_ids = [s.id for s in sessions_by_lesson.values()]
    participant_map = {}
    for p in SessionParticipant.objects.filter(
        session_id__in=session_ids,
        student_id__in=student_ids,
    ):
        participant_map[(p.session_id, p.student_id)] = p

    # Build result
    students_data = []
    for rel in relationships:
        lesson = recent_lessons.get(rel.student_id)
        error_count = error_counts.get(lesson.id, 0) if lesson else 0

        # Use denormalized latest_level from TutoringRelationship
        level = rel.latest_level or rel.current_level or ""

        practice_completed = False
        practice_score = None
        if lesson:
            session = sessions_by_lesson.get(lesson.id)
            if session:
                participant = participant_map.get((session.id, rel.student_id))
                if participant:
                    practice_completed = participant.completed_at is not None
                    if participant.results_data:
                        practice_score = participant.results_data.get("score")

        # Attention flag from recurring error patterns
        attention_flag = None
        recurring_patterns = (
            ErrorPattern.objects.filter(
                student_id=rel.student_id,
                teacher_id=teacher_id,
                status=ErrorPatternStatus.RECURRING,
            )
            .order_by("-occurrence_count")
            .first()
        )
        if recurring_patterns:
            attention_flag = f"{recurring_patterns.label} - recurring across {recurring_patterns.lesson_count} lessons"

        students_data.append(
            {
                "name": rel.student.name,
                "level": level,
                "practice_completed": practice_completed,
                "practice_score": practice_score,
                "error_count": error_count,
                "active_patterns": rel.active_error_patterns,
                "mastered_patterns": rel.mastered_error_patterns,
                "attention_flag": attention_flag,
                "next_lesson": None,
                "schedule": rel.schedule or None,
            }
        )

    return students_data


@register_tool
class QueryDailyOverviewTool(PreplyTool):
    @property
    def name(self):
        return "query_daily_overview"

    @property
    def description(self):
        return "Get today's overview of all students. Shows practice scores, error patterns, and attention flags."

    @property
    def args_schema(self):
        return QueryDailyOverviewArgs

    async def execute(self, *, conversation=None):
        students_data = None

        if conversation and conversation.teacher_id:
            students_data = await _fetch_daily_overview(conversation.teacher_id)

        if not students_data:
            return self._mock_daily_overview()

        data = {
            "widget_type": "daily_overview",
            "date": str(date.today()),
            "students": students_data,
        }

        completed = sum(1 for s in students_data if s["practice_completed"])
        flagged = sum(1 for s in students_data if s.get("attention_flag"))
        message = f"{len(students_data)} students today. {completed} completed practice, {flagged} need attention."
        return message, data

    def _mock_daily_overview(self):
        data = {
            "widget_type": "daily_overview",
            "date": str(date.today()),
            "students": [
                {
                    "name": "Maria Garcia",
                    "level": "B1",
                    "practice_completed": True,
                    "practice_score": 75,
                    "error_count": 4,
                    "active_patterns": 2,
                    "mastered_patterns": 1,
                    "attention_flag": "Past tense errors recurring across 3 lessons",
                    "next_lesson": "10:00",
                },
                {
                    "name": "Alex Chen",
                    "level": "A2",
                    "practice_completed": True,
                    "practice_score": 88,
                    "error_count": 2,
                    "active_patterns": 1,
                    "mastered_patterns": 0,
                    "attention_flag": None,
                    "next_lesson": "11:30",
                },
                {
                    "name": "Sophie Martin",
                    "level": "B2",
                    "practice_completed": False,
                    "practice_score": None,
                    "error_count": 3,
                    "active_patterns": 0,
                    "mastered_patterns": 2,
                    "attention_flag": "Practice not completed - 2nd time this week",
                    "next_lesson": "14:00",
                },
            ],
        }

        completed = sum(1 for s in data["students"] if s["practice_completed"])
        flagged = sum(1 for s in data["students"] if s["attention_flag"])
        message = f"{len(data['students'])} students today. {completed} completed practice, {flagged} need attention."
        return message, data
