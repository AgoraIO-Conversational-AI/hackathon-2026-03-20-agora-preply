"""Tests for learning progress services - pattern status state machine."""

import pytest

from apps.learning_progress.models import ErrorPatternStatus
from apps.learning_progress.services import (
    update_mastery_after_result,
    update_pattern_status,
    update_tutoring_relationship_counts,
)
from tests.factories import (
    ErrorPatternFactory,
    StudentFactory,
    TeacherFactory,
    TutoringRelationshipFactory,
)


@pytest.mark.django_db
class TestUpdatePatternStatus:
    def test_new_pattern_stays_new(self):
        pattern = ErrorPatternFactory(lesson_count=1, times_tested=0)

        update_pattern_status(pattern)

        pattern.refresh_from_db()
        assert pattern.status == ErrorPatternStatus.NEW

    def test_becomes_recurring(self):
        pattern = ErrorPatternFactory(lesson_count=2, times_tested=0)

        update_pattern_status(pattern)

        pattern.refresh_from_db()
        assert pattern.status == ErrorPatternStatus.RECURRING

    def test_becomes_improving(self):
        pattern = ErrorPatternFactory(
            lesson_count=2,
            times_tested=2,
            times_correct=1,
            mastery_score=0.6,
        )

        update_pattern_status(pattern)

        pattern.refresh_from_db()
        assert pattern.status == ErrorPatternStatus.IMPROVING

    def test_becomes_mastered(self):
        pattern = ErrorPatternFactory(
            lesson_count=2,
            times_tested=4,
            times_correct=4,
            mastery_score=0.9,
        )

        update_pattern_status(pattern)

        pattern.refresh_from_db()
        assert pattern.status == ErrorPatternStatus.MASTERED


@pytest.mark.django_db
class TestUpdateMasteryAfterResult:
    def test_increments_and_recalculates(self):
        pattern = ErrorPatternFactory(
            times_tested=2,
            times_correct=1,
            mastery_score=0.5,
        )

        update_mastery_after_result(pattern, is_correct=True)

        pattern.refresh_from_db()
        assert pattern.times_tested == 3
        assert pattern.times_correct == 2
        assert abs(pattern.mastery_score - 2 / 3) < 0.01

    def test_incorrect_result(self):
        pattern = ErrorPatternFactory(
            times_tested=1,
            times_correct=1,
            mastery_score=1.0,
        )

        update_mastery_after_result(pattern, is_correct=False)

        pattern.refresh_from_db()
        assert pattern.times_tested == 2
        assert pattern.times_correct == 1
        assert pattern.mastery_score == 0.5


@pytest.mark.django_db
class TestUpdateTutoringRelationshipCounts:
    def test_counts_active_and_mastered(self):
        teacher = TeacherFactory()
        student = StudentFactory()
        rel = TutoringRelationshipFactory(teacher=teacher, student=student)

        ErrorPatternFactory(student=student, teacher=teacher, status=ErrorPatternStatus.NEW)
        ErrorPatternFactory(student=student, teacher=teacher, status=ErrorPatternStatus.RECURRING)
        ErrorPatternFactory(student=student, teacher=teacher, status=ErrorPatternStatus.MASTERED)

        update_tutoring_relationship_counts(teacher.id, student.id)

        rel.refresh_from_db()
        assert rel.active_error_patterns == 2  # new + recurring
        assert rel.mastered_error_patterns == 1
