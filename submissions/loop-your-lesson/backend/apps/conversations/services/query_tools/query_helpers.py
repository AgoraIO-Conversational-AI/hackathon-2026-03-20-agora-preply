"""Shared helpers for query tools."""

from asgiref.sync import sync_to_async

from apps.skill_results.models import SkillExecution, SkillExecutionStatus


@sync_to_async
def get_skill_output(lesson_id, skill_name):
    """Fetch output_data from a completed SkillExecution for a lesson."""
    execution = SkillExecution.objects.filter(
        lesson_id=lesson_id,
        skill_name=skill_name,
        status=SkillExecutionStatus.COMPLETED,
    ).first()
    return execution.output_data if execution else None


@sync_to_async
def get_skill_output_by_student(student_id, skill_name):
    """Fetch most recent output_data for a student (any lesson)."""
    execution = (
        SkillExecution.objects.filter(
            student_id=student_id,
            skill_name=skill_name,
            status=SkillExecutionStatus.COMPLETED,
        )
        .order_by("-created_at")
        .first()
    )
    return execution.output_data if execution else None
