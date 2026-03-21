"""Error pattern status state machine and progress tracking."""

from __future__ import annotations

import logging

from apps.learning_progress.models import ErrorPattern, ErrorPatternStatus

logger = logging.getLogger(__name__)


def update_pattern_status(pattern: ErrorPattern) -> None:
    """Update an ErrorPattern's status based on occurrence and mastery data.

    State machine:
        new       -> first occurrence (1 lesson)
        recurring -> seen in 2+ lessons, or tested with mastery < 0.5
        improving -> tested with mastery 0.5-0.8
        mastered  -> tested 3+ times with mastery > 0.8
        mastered can revert to recurring if pattern reappears in new lesson
    """
    old_status = pattern.status

    if pattern.times_tested >= 3 and pattern.mastery_score is not None and pattern.mastery_score > 0.8:
        pattern.status = ErrorPatternStatus.MASTERED
    elif pattern.times_tested > 0 and pattern.mastery_score is not None and pattern.mastery_score >= 0.5:
        pattern.status = ErrorPatternStatus.IMPROVING
    elif pattern.lesson_count >= 2:
        pattern.status = ErrorPatternStatus.RECURRING
    else:
        pattern.status = ErrorPatternStatus.NEW

    if old_status != pattern.status:
        logger.info(
            "Pattern %s status: %s -> %s (lessons=%d, tested=%d, mastery=%s)",
            pattern.pattern_key,
            old_status,
            pattern.status,
            pattern.lesson_count,
            pattern.times_tested,
            pattern.mastery_score,
        )
        pattern.save(update_fields=["status", "updated_at"])


def update_mastery_after_result(pattern: ErrorPattern, is_correct: bool) -> None:
    """Update pattern mastery after a practice result."""
    pattern.times_tested += 1
    if is_correct:
        pattern.times_correct += 1
    pattern.mastery_score = pattern.times_correct / pattern.times_tested if pattern.times_tested > 0 else None
    pattern.save(update_fields=["times_tested", "times_correct", "mastery_score", "updated_at"])
    update_pattern_status(pattern)


def update_tutoring_relationship_counts(teacher_id, student_id) -> None:
    """Update denormalized error pattern counts on TutoringRelationship."""
    from apps.tutoring.models import TutoringRelationship

    relationships = TutoringRelationship.objects.filter(teacher_id=teacher_id, student_id=student_id)
    for rel in relationships:
        rel.active_error_patterns = ErrorPattern.objects.filter(
            student_id=student_id,
            teacher_id=teacher_id,
            status__in=[ErrorPatternStatus.NEW, ErrorPatternStatus.RECURRING],
        ).count()
        rel.mastered_error_patterns = ErrorPattern.objects.filter(
            student_id=student_id,
            teacher_id=teacher_id,
            status=ErrorPatternStatus.MASTERED,
        ).count()
        rel.save(update_fields=["active_error_patterns", "mastered_error_patterns", "updated_at"])
