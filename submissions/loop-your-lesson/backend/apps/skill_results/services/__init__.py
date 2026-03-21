"""SkillExecution state machine: PENDING -> RUNNING -> COMPLETED/FAILED."""

from __future__ import annotations

import logging

from django.utils import timezone

from apps.skill_results.models import SkillExecution, SkillExecutionStatus

logger = logging.getLogger(__name__)


def create_execution(
    teacher,
    skill_name: str,
    *,
    lesson=None,
    student=None,
    input_data: dict | None = None,
) -> SkillExecution:
    """Create a new pending skill execution."""
    return SkillExecution.objects.create(
        teacher=teacher,
        lesson=lesson,
        student=student,
        skill_name=skill_name,
        input_data=input_data or {},
    )


def start_execution(execution: SkillExecution) -> SkillExecution:
    """Mark execution as running."""
    execution.status = SkillExecutionStatus.RUNNING
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at", "updated_at"])
    logger.info("Started %s execution %s", execution.skill_name, execution.id)
    return execution


def complete_execution(execution: SkillExecution, output_data: dict) -> SkillExecution:
    """Mark execution as completed with output data, then parse into structured models."""
    from apps.skill_results.services.parsers import parse_skill_output

    execution.status = SkillExecutionStatus.COMPLETED
    execution.completed_at = timezone.now()
    execution.output_data = output_data
    execution.save(update_fields=["status", "completed_at", "output_data", "updated_at"])
    logger.info("Completed %s execution %s", execution.skill_name, execution.id)

    # Parse output into structured models
    parse_skill_output(execution)

    return execution


def fail_execution(execution: SkillExecution, error: str, exit_code: int | None = None) -> SkillExecution:
    """Mark execution as failed."""
    execution.status = SkillExecutionStatus.FAILED
    execution.completed_at = timezone.now()
    execution.error = error
    execution.exit_code = exit_code
    execution.save(update_fields=["status", "completed_at", "error", "exit_code", "updated_at"])
    logger.warning("Failed %s execution %s: %s", execution.skill_name, execution.id, error)
    return execution


def get_latest_output(student_id, skill_name: str, lesson_id=None) -> dict:
    """Get the most recent completed output for a student + skill."""
    qs = SkillExecution.objects.filter(
        student_id=student_id,
        skill_name=skill_name,
        status=SkillExecutionStatus.COMPLETED,
    )
    if lesson_id:
        qs = qs.filter(lesson_id=lesson_id)
    execution = qs.order_by("-completed_at").first()
    return execution.output_data if execution else {}
