"""Tests for skill output parsers."""

import pytest

from apps.classtime_sessions.models import PracticeQuestion
from apps.learning_progress.models import (
    ErrorPattern,
    ErrorPatternOccurrence,
    ErrorPatternStatus,
    LessonLevelAssessment,
)
from apps.skill_results.models import ErrorRecord, LessonTheme, SkillExecutionStatus, SkillName
from apps.skill_results.services.parsers import parse_all_for_lesson, parse_skill_output
from apps.tutoring.models import TutoringRelationship
from tests.factories import (
    ClasstimeSessionFactory,
    ErrorPatternFactory,
    LessonFactory,
    SkillExecutionFactory,
    StudentFactory,
    TeacherFactory,
    TutoringRelationshipFactory,
)


@pytest.fixture
def lesson_setup():
    teacher = TeacherFactory()
    student = StudentFactory()
    lesson = LessonFactory(teacher=teacher)
    return teacher, student, lesson


# --- Error parser ---


@pytest.mark.django_db
class TestParseErrorOutput:
    def test_creates_error_records(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "verb_tense",
                        "severity": "moderate",
                        "original": "I go yesterday",
                        "corrected": "I went yesterday",
                        "explanation": "Past simple",
                        "error_index": 1,
                        "timestamp": "12:45",
                        "l1_transfer": False,
                    },
                    {
                        "type": "vocabulary",
                        "subtype": "collocation",
                        "severity": "minor",
                        "original": "make a travel",
                        "corrected": "take a trip",
                        "explanation": "Collocation error",
                        "error_index": 2,
                        "timestamp": "18:20",
                        "l1_transfer": True,
                    },
                ],
            },
        )

        parse_skill_output(execution)

        assert ErrorRecord.objects.filter(lesson=lesson).count() == 2
        r1 = ErrorRecord.objects.get(source_error_index=1)
        assert r1.error_type == "grammar"
        assert r1.severity == "moderate"
        assert r1.l1_transfer is False

    def test_creates_patterns_and_occurrences(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "case_declension",
                        "severity": "moderate",
                        "original": "przerywat mnie",
                        "corrected": "przerywac mi",
                        "explanation": "Dative required",
                        "error_index": 1,
                    },
                    {
                        "type": "grammar",
                        "subtype": "case_declension",
                        "severity": "moderate",
                        "original": "dla niego",
                        "corrected": "jemu",
                        "explanation": "Dative avoidance",
                        "error_index": 2,
                    },
                ],
                "error_patterns": [
                    {"pattern": "Dative case avoidance", "error_ids": [1, 2]},
                ],
            },
        )

        parse_skill_output(execution)

        assert ErrorPattern.objects.count() == 1
        pattern = ErrorPattern.objects.first()
        assert pattern.label == "Dative case avoidance"
        assert pattern.occurrence_count == 2
        assert pattern.lesson_count == 1
        assert pattern.status == ErrorPatternStatus.NEW
        assert ErrorPatternOccurrence.objects.count() == 2

    def test_updates_existing_pattern(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        lesson2 = LessonFactory(teacher=teacher)

        # First lesson creates pattern
        exec1 = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "verb_tense",
                        "severity": "moderate",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 1,
                    }
                ],
                "error_patterns": [{"pattern": "Past tense errors", "error_ids": [1]}],
            },
        )
        parse_skill_output(exec1)

        # Second lesson adds to pattern
        exec2 = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson2,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "verb_tense",
                        "severity": "moderate",
                        "original": "d",
                        "corrected": "e",
                        "explanation": "f",
                        "error_index": 1,
                    }
                ],
                "error_patterns": [{"pattern": "Past tense errors", "error_ids": [1]}],
            },
        )
        parse_skill_output(exec2)

        assert ErrorPattern.objects.count() == 1
        pattern = ErrorPattern.objects.first()
        assert pattern.occurrence_count == 2
        assert pattern.lesson_count == 2
        assert pattern.status == ErrorPatternStatus.RECURRING

    def test_reverts_mastered_pattern(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        pattern = ErrorPatternFactory(
            student=student,
            teacher=teacher,
            pattern_key="grammar:verb_tense:past_tense_errors",
            status=ErrorPatternStatus.MASTERED,
            lesson_count=2,
            occurrence_count=3,
            times_tested=4,
            times_correct=4,
            mastery_score=1.0,
        )

        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "verb_tense",
                        "severity": "moderate",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 1,
                    }
                ],
                "error_patterns": [{"pattern": "Past tense errors", "error_ids": [1]}],
            },
        )
        parse_skill_output(execution)

        pattern.refresh_from_db()
        assert pattern.status == ErrorPatternStatus.RECURRING

    def test_handles_l1_transfer_string_format(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "preposition",
                        "severity": "major",
                        "original": "ukryc od",
                        "corrected": "ukryc przed",
                        "explanation": "Preposition",
                        "error_index": 1,
                        "l1_transfer": "yes - Ukrainian 'vid' maps to 'od'",
                    },
                ],
            },
        )

        parse_skill_output(execution)

        record = ErrorRecord.objects.first()
        assert record.l1_transfer is True
        assert "Ukrainian" in record.l1_transfer_explanation


# --- Level parser ---


@pytest.mark.django_db
class TestParseLevelOutput:
    def test_creates_assessment(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_LEVEL,
            output_data={
                "level": "B1+",
                "dimensions": {
                    "range": {"level": "B1+"},
                    "accuracy": {"level": "B1"},
                    "fluency": {"level": "B1+"},
                    "interaction": {"level": "B1+"},
                    "coherence": {"level": "B1"},
                },
                "strengths": ["Good fluency", "Natural interaction"],
                "gaps": ["Prepositional governance"],
                "zpd": {"lower_bound": "B1", "upper_bound": "B2"},
            },
        )

        parse_skill_output(execution)

        assert LessonLevelAssessment.objects.count() == 1
        assessment = LessonLevelAssessment.objects.first()
        assert assessment.overall_level == "B1+"
        assert assessment.range_level == "B1+"
        assert assessment.accuracy_level == "B1"
        assert assessment.zpd_lower == "B1"
        assert len(assessment.strengths) == 2
        assert len(assessment.gaps) == 1

    def test_updates_tutoring_relationship(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        TutoringRelationshipFactory(teacher=teacher, student=student)
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_LEVEL,
            output_data={"level": "B2"},
        )

        parse_skill_output(execution)

        rel = TutoringRelationship.objects.first()
        assert rel.latest_level == "B2"
        assert rel.latest_level_assessed_at is not None

    def test_handles_missing_dimensions(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_LEVEL,
            output_data={"level": "A2"},
        )

        parse_skill_output(execution)

        assessment = LessonLevelAssessment.objects.first()
        assert assessment.overall_level == "A2"
        assert assessment.range_level == ""


# --- Theme parser ---


@pytest.mark.django_db
class TestParseThemeOutput:
    def test_creates_themes(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_THEMES,
            output_data={
                "themes": [
                    {
                        "topic": "Travel planning",
                        "communicative_function": "explaining",
                        "initiated_by": "student",
                        "vocabulary_active": [{"term": "trip", "level": "A2"}],
                        "vocabulary_passive": [],
                        "chunks": ["take a trip"],
                        "transcript_range": {"start": "02:00", "end": "15:30"},
                    },
                    {"topic": "Food", "transcript_range": {"start": "16:00", "end": "28:00"}},
                ],
            },
        )

        parse_skill_output(execution)

        assert LessonTheme.objects.count() == 2
        theme = LessonTheme.objects.filter(topic="Travel planning").first()
        assert theme.communicative_function == "explaining"
        assert theme.transcript_range_start == "02:00"
        assert len(theme.vocabulary_active) == 1

    def test_handles_string_range(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_THEMES,
            output_data={
                "themes": [{"topic": "Topic A", "transcript_range": "00:10 - 02:00"}],
            },
        )

        parse_skill_output(execution)

        theme = LessonTheme.objects.first()
        assert theme.transcript_range_start == "00:10"
        assert theme.transcript_range_end == "02:00"


# --- Question parser ---


@pytest.mark.django_db
class TestParseQuestionOutput:
    def test_links_to_error_record(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        # Create error records first
        error_exec = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "case_declension",
                        "severity": "moderate",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 4,
                    },
                ],
            },
        )
        parse_skill_output(error_exec)

        # Create session and question execution
        session = ClasstimeSessionFactory(teacher=teacher, lesson=lesson)
        q_exec = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.GENERATE_QUESTIONS,
            output_data={
                "questions": [
                    {
                        "source_ref": {
                            "error_index": 4,
                            "error_type": "grammar",
                            "subtype": "case_declension",
                            "pattern_ref": "dative",
                        },
                        "payload_type": "gap",
                        "difficulty": "zpd_target",
                        "payload": {"template_text": "On {0} przerywat.", "title": "Dative"},
                    }
                ],
            },
        )
        session.question_skill_execution = q_exec
        session.save()

        parse_skill_output(q_exec)

        pq = PracticeQuestion.objects.first()
        assert pq is not None
        assert pq.error_record is not None
        assert pq.error_record.source_error_index == 4
        assert pq.question_type == "gap"
        assert pq.difficulty == "zpd_target"

    def test_stem_extraction(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        session = ClasstimeSessionFactory(teacher=teacher, lesson=lesson)
        q_exec = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.GENERATE_QUESTIONS,
            output_data={
                "questions": [
                    {
                        "source_ref": {},
                        "payload_type": "gap",
                        "payload": {"template_text": "Fill: {0}", "title": "Gap Q"},
                    },
                    {"source_ref": {}, "payload_type": "choice", "payload": {"title": "Which is correct?"}},
                ],
            },
        )
        session.question_skill_execution = q_exec
        session.save()

        parse_skill_output(q_exec)

        questions = list(PracticeQuestion.objects.order_by("question_index"))
        assert questions[0].stem == "Fill: {0}"  # gap -> template_text
        assert questions[1].stem == "Which is correct?"  # choice -> title


# --- Dispatcher ---


@pytest.mark.django_db
class TestParseDispatcher:
    def test_idempotent(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "x",
                        "severity": "minor",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 1,
                    },
                ]
            },
        )

        parse_skill_output(execution)
        count_after_first = ErrorRecord.objects.count()

        parse_skill_output(execution)
        assert ErrorRecord.objects.count() == count_after_first

    def test_skips_non_completed(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        execution = SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            status=SkillExecutionStatus.PENDING,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "x",
                        "severity": "minor",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 1,
                    },
                ]
            },
        )

        parse_skill_output(execution)

        assert ErrorRecord.objects.count() == 0

    def test_parse_all_for_lesson(self, lesson_setup):
        teacher, student, lesson = lesson_setup
        SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_ERRORS,
            output_data={
                "errors": [
                    {
                        "type": "grammar",
                        "subtype": "x",
                        "severity": "minor",
                        "original": "a",
                        "corrected": "b",
                        "explanation": "c",
                        "error_index": 1,
                    },
                ]
            },
        )
        SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_LEVEL,
            output_data={"level": "B1"},
        )
        SkillExecutionFactory(
            teacher=teacher,
            lesson=lesson,
            student=student,
            skill_name=SkillName.ANALYZE_THEMES,
            output_data={"themes": [{"topic": "Travel"}]},
        )

        parse_all_for_lesson(lesson.id, teacher.id)

        assert ErrorRecord.objects.count() == 1
        assert LessonLevelAssessment.objects.count() == 1
        assert LessonTheme.objects.count() == 1
