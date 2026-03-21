import asyncio
from datetime import date

import pytest
from django.utils import timezone

from apps.accounts.models import Student, Teacher
from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant
from apps.conversations.models import Conversation, ConversationStatus
from apps.conversations.services.query_tools.query_classtime_results import QueryClasstimeResultsTool
from apps.conversations.services.query_tools.query_daily_overview import QueryDailyOverviewTool
from apps.conversations.services.query_tools.query_error_trends import QueryErrorTrendsTool
from apps.conversations.services.query_tools.query_lesson_errors import QueryLessonErrorsTool
from apps.conversations.services.query_tools.query_lesson_themes import QueryLessonThemesTool
from apps.conversations.services.query_tools.query_practice_mastery import QueryPracticeMasteryTool
from apps.learning_progress.models import ErrorPattern
from apps.lessons.models import Lesson, LessonStudent
from apps.skill_results.models import ErrorRecord, LessonTheme, SkillExecution
from apps.tutoring.models import TutoringRelationship


@pytest.fixture
def db_teacher():
    return Teacher.objects.create(name="Test Teacher", email="t@test.com")


@pytest.fixture
def db_student():
    return Student.objects.create(name="Test Student", email="s@test.com")


@pytest.fixture
def db_lesson(db_teacher):
    return Lesson.objects.create(
        teacher=db_teacher,
        subject_type="language",
        date=date(2026, 3, 14),
        duration_minutes=50,
        transcript_summary="Test lesson summary",
    )


@pytest.fixture
def db_lesson_student(db_lesson, db_student):
    return LessonStudent.objects.create(lesson=db_lesson, student=db_student)


@pytest.fixture
def db_error_execution(db_teacher, db_lesson, db_student):
    execution = SkillExecution.objects.create(
        teacher=db_teacher,
        lesson=db_lesson,
        student=db_student,
        skill_name="analyze-lesson-errors",
        status="completed",
        output_data={
            "errors": [
                {
                    "type": "grammar",
                    "severity": "moderate",
                    "original": "I go yesterday",
                    "corrected": "I went yesterday",
                    "explanation": "Past simple",
                    "position": {"utterance": 1, "timestamp": "01:00"},
                },
                {
                    "type": "vocabulary",
                    "severity": "minor",
                    "original": "make a travel",
                    "corrected": "take a trip",
                    "explanation": "Collocation",
                    "position": {"utterance": 2, "timestamp": "02:00"},
                },
            ],
            "summary": {"total": 2},
        },
    )
    # Create structured ErrorRecord rows
    ErrorRecord.objects.create(
        skill_execution=execution,
        lesson=db_lesson,
        student=db_student,
        error_type="grammar",
        error_subtype="verb_tense",
        severity="moderate",
        original_text="I go yesterday",
        corrected_text="I went yesterday",
        explanation="Past simple",
        timestamp="01:00",
        utterance_index=1,
        source_error_index=1,
    )
    ErrorRecord.objects.create(
        skill_execution=execution,
        lesson=db_lesson,
        student=db_student,
        error_type="vocabulary",
        error_subtype="collocation",
        severity="minor",
        original_text="make a travel",
        corrected_text="take a trip",
        explanation="Collocation",
        timestamp="02:00",
        utterance_index=2,
        source_error_index=2,
    )
    return execution


@pytest.fixture
def db_theme_execution(db_teacher, db_lesson, db_student):
    execution = SkillExecution.objects.create(
        teacher=db_teacher,
        lesson=db_lesson,
        student=db_student,
        skill_name="analyze-lesson-themes",
        status="completed",
        output_data={
            "themes": [
                {"topic": "Travel", "vocabulary": ["trip", "flight"], "utterance_count": 10},
            ],
        },
    )
    # Create structured LessonTheme row
    LessonTheme.objects.create(
        skill_execution=execution,
        lesson=db_lesson,
        student=db_student,
        topic="Travel",
        vocabulary_active=["trip", "flight"],
    )
    return execution


@pytest.fixture
def db_student_conversation(db_teacher, db_student, db_lesson):
    return Conversation.objects.create(
        mode="student_practice",
        status=ConversationStatus.ACTIVE,
        teacher=db_teacher,
        student=db_student,
        lesson=db_lesson,
    )


@pytest.fixture
def db_teacher_conversation(db_teacher):
    return Conversation.objects.create(
        mode="daily_briefing",
        status=ConversationStatus.ACTIVE,
        teacher=db_teacher,
    )


@pytest.mark.django_db(transaction=True)
class TestQueryLessonErrorsTool:
    def test_returns_real_errors(self, db_student_conversation, db_error_execution):
        msg, data = asyncio.run(QueryLessonErrorsTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "error_analysis"
        assert len(data["errors"]) == 2
        assert data["errors"][0]["original"] == "I go yesterday"

    def test_filters_by_type(self, db_student_conversation, db_error_execution):
        msg, data = asyncio.run(
            QueryLessonErrorsTool().execute(conversation=db_student_conversation, error_type="grammar")
        )
        assert len(data["errors"]) == 1
        assert data["errors"][0]["type"] == "grammar"

    def test_filters_by_severity(self, db_student_conversation, db_error_execution):
        msg, data = asyncio.run(QueryLessonErrorsTool().execute(conversation=db_student_conversation, severity="minor"))
        assert len(data["errors"]) == 1
        assert data["errors"][0]["severity"] == "minor"

    def test_falls_back_to_mock_without_conversation(self):
        msg, data = asyncio.run(QueryLessonErrorsTool().execute())
        assert data["widget_type"] == "error_analysis"
        assert len(data["errors"]) > 0

    def test_falls_back_to_mock_without_skill_execution(self, db_student_conversation):
        msg, data = asyncio.run(QueryLessonErrorsTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "error_analysis"
        assert len(data["errors"]) > 0


@pytest.mark.django_db(transaction=True)
class TestQueryLessonThemesTool:
    def test_returns_real_themes(self, db_student_conversation, db_theme_execution):
        msg, data = asyncio.run(QueryLessonThemesTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "theme_map"
        assert len(data["themes"]) == 1
        assert data["themes"][0]["topic"] == "Travel"

    def test_falls_back_to_mock_without_execution(self, db_student_conversation):
        msg, data = asyncio.run(QueryLessonThemesTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "theme_map"
        assert len(data["themes"]) > 0


@pytest.mark.django_db(transaction=True)
class TestQueryDailyOverviewTool:
    def test_returns_students_for_teacher(
        self, db_teacher, db_student, db_lesson, db_lesson_student, db_error_execution, db_teacher_conversation
    ):
        TutoringRelationship.objects.create(
            teacher=db_teacher,
            student=db_student,
            subject_type="language",
            current_level="B1",
            status="active",
        )
        msg, data = asyncio.run(QueryDailyOverviewTool().execute(conversation=db_teacher_conversation))
        assert data["widget_type"] == "daily_overview"
        assert len(data["students"]) == 1
        assert data["students"][0]["name"] == "Test Student"
        assert data["students"][0]["error_count"] == 2

    def test_falls_back_to_mock_without_teacher(self):
        msg, data = asyncio.run(QueryDailyOverviewTool().execute())
        assert data["widget_type"] == "daily_overview"
        assert len(data["students"]) > 0


@pytest.mark.django_db(transaction=True)
class TestQueryClasstimeResultsTool:
    def test_returns_real_practice_results(self, db_teacher, db_student, db_lesson, db_student_conversation):


        session = ClasstimeSession.objects.create(
            lesson=db_lesson,
            teacher=db_teacher,
            session_code="TEST-001",
            status="completed",
        )
        SessionParticipant.objects.create(
            session=session,
            student=db_student,
            completed_at=timezone.now(),
            results_data={
                "score": 8,
                "total": 10,
                "percentage": 80,
                "questions": [
                    {"question": "Test?", "correct": True},
                    {"question": "Test2?", "correct": False},
                ],
            },
        )
        msg, data = asyncio.run(QueryClasstimeResultsTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "practice_results"
        assert data["score"] == 8
        assert data["percentage"] == 80
        assert len(data["questions"]) == 2

    def test_suggests_create_tool_without_session(self, db_student_conversation):
        msg, data = asyncio.run(QueryClasstimeResultsTool().execute(conversation=db_student_conversation))
        assert data == {}
        assert "create_practice_session" in msg

    def test_returns_practice_card_when_not_completed(self, db_teacher, db_student, db_lesson, db_student_conversation):
        session = ClasstimeSession.objects.create(
            lesson=db_lesson,
            teacher=db_teacher,
            session_code="TEST-002",
            status="created",
            student_url="https://www.classtime.com/code/TEST-002",
        )
        SessionParticipant.objects.create(
            session=session,
            student=db_student,
        )
        msg, data = asyncio.run(QueryClasstimeResultsTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "practice_card"
        assert data["session_url"] == "https://www.classtime.com/code/TEST-002"


@pytest.mark.django_db(transaction=True)
class TestQueryErrorTrendsTool:
    def test_returns_patterns(self, db_teacher, db_student, db_student_conversation):


        now = timezone.now()
        ErrorPattern.objects.create(
            student=db_student,
            teacher=db_teacher,
            pattern_key="grammar:verb_tense:past_simple",
            label="Past simple errors",
            error_type="grammar",
            error_subtype="verb_tense",
            status="recurring",
            first_seen_at=now,
            last_seen_at=now,
            occurrence_count=5,
            lesson_count=2,
        )
        msg, data = asyncio.run(QueryErrorTrendsTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "error_trends"
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["label"] == "Past simple errors"

    def test_filters_by_status(self, db_teacher, db_student, db_student_conversation):


        now = timezone.now()
        ErrorPattern.objects.create(
            student=db_student,
            teacher=db_teacher,
            pattern_key="grammar:a:b",
            label="A",
            error_type="grammar",
            status="recurring",
            first_seen_at=now,
            last_seen_at=now,
        )
        ErrorPattern.objects.create(
            student=db_student,
            teacher=db_teacher,
            pattern_key="grammar:c:d",
            label="B",
            error_type="grammar",
            status="mastered",
            first_seen_at=now,
            last_seen_at=now,
        )
        msg, data = asyncio.run(
            QueryErrorTrendsTool().execute(conversation=db_student_conversation, status="recurring")
        )
        assert len(data["patterns"]) == 1

    def test_falls_back_to_mock(self):
        msg, data = asyncio.run(QueryErrorTrendsTool().execute())
        assert data["widget_type"] == "error_trends"
        assert len(data["patterns"]) > 0


@pytest.mark.django_db(transaction=True)
class TestQueryPracticeMasteryTool:
    def test_returns_mastery_data(self, db_teacher, db_student, db_student_conversation):


        now = timezone.now()
        ErrorPattern.objects.create(
            student=db_student,
            teacher=db_teacher,
            pattern_key="grammar:x:y",
            label="Test pattern",
            error_type="grammar",
            status="improving",
            first_seen_at=now,
            last_seen_at=now,
            times_tested=3,
            times_correct=2,
            mastery_score=0.67,
        )
        msg, data = asyncio.run(QueryPracticeMasteryTool().execute(conversation=db_student_conversation))
        assert data["widget_type"] == "practice_mastery"
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["mastery_score"] == 0.67

    def test_falls_back_to_mock(self):
        msg, data = asyncio.run(QueryPracticeMasteryTool().execute())
        assert data["widget_type"] == "practice_mastery"
        assert len(data["patterns"]) > 0
