"""Tests for SkillExecution state machine."""

import pytest

from apps.skill_results.models import SkillExecutionStatus, SkillName
from apps.skill_results.services import (
    complete_execution,
    create_execution,
    fail_execution,
    get_latest_output,
    start_execution,
)
from tests.factories import LessonFactory, StudentFactory, TeacherFactory


@pytest.mark.django_db
class TestSkillExecutionStateMachine:
    def test_create_execution(self):
        teacher = TeacherFactory()
        lesson = LessonFactory(teacher=teacher)
        student = StudentFactory()

        execution = create_execution(teacher, SkillName.ANALYZE_ERRORS, lesson=lesson, student=student)

        assert execution.status == SkillExecutionStatus.PENDING
        assert execution.skill_name == SkillName.ANALYZE_ERRORS
        assert execution.teacher == teacher
        assert execution.lesson == lesson
        assert execution.student == student

    def test_start_execution(self):
        teacher = TeacherFactory()
        lesson = LessonFactory(teacher=teacher)
        student = StudentFactory()
        execution = create_execution(teacher, SkillName.ANALYZE_ERRORS, lesson=lesson, student=student)

        start_execution(execution)

        execution.refresh_from_db()
        assert execution.status == SkillExecutionStatus.RUNNING
        assert execution.started_at is not None

    def test_complete_execution(self):
        teacher = TeacherFactory()
        lesson = LessonFactory(teacher=teacher)
        student = StudentFactory()
        execution = create_execution(teacher, SkillName.ANALYZE_ERRORS, lesson=lesson, student=student)
        output = {"errors": [], "summary": {"total": 0}}

        complete_execution(execution, output)

        execution.refresh_from_db()
        assert execution.status == SkillExecutionStatus.COMPLETED
        assert execution.completed_at is not None
        assert execution.output_data == output
        assert execution.parsed_at is not None  # Parser was called

    def test_fail_execution(self):
        teacher = TeacherFactory()
        lesson = LessonFactory(teacher=teacher)
        student = StudentFactory()
        execution = create_execution(teacher, SkillName.ANALYZE_ERRORS, lesson=lesson, student=student)

        fail_execution(execution, "Something went wrong", exit_code=1)

        execution.refresh_from_db()
        assert execution.status == SkillExecutionStatus.FAILED
        assert execution.error == "Something went wrong"
        assert execution.exit_code == 1
        assert execution.completed_at is not None

    def test_get_latest_output(self):
        teacher = TeacherFactory()
        lesson = LessonFactory(teacher=teacher)
        student = StudentFactory()
        output = {"errors": [{"type": "grammar"}]}
        execution = create_execution(teacher, SkillName.ANALYZE_ERRORS, lesson=lesson, student=student)
        complete_execution(execution, output)

        result = get_latest_output(student.id, SkillName.ANALYZE_ERRORS)

        assert result == output

    def test_get_latest_output_returns_empty_when_none(self):
        student = StudentFactory()

        result = get_latest_output(student.id, SkillName.ANALYZE_ERRORS)

        assert result == {}
