"""Parse completed SkillExecution output_data into structured models.

Execution order is strict due to FK dependencies:
    1. _parse_error_output   -> ErrorRecord + ErrorPattern
    2. _parse_level_output   -> LessonLevelAssessment
    3. _parse_theme_output   -> LessonTheme
    4. _parse_question_output -> PracticeQuestion (links to ErrorRecord + ErrorPattern)
"""

from __future__ import annotations

import logging
import re

from django.db import transaction
from django.utils import timezone

from apps.learning_progress.models import (
    ErrorPattern,
    ErrorPatternOccurrence,
    ErrorPatternStatus,
    LessonLevelAssessment,
)
from apps.learning_progress.services import (
    update_tutoring_relationship_counts,
)
from apps.skill_results.models import (
    ErrorRecord,
    LessonTheme,
    SkillExecution,
    SkillExecutionStatus,
    SkillName,
)

logger = logging.getLogger(__name__)

# Stem extraction per payload_type
_STEM_FIELD = {
    "gap": "template_text",
    "choice": "title",
    "boolean": "title",
    "sorter": "title",
    "categorizer": "title",
    "multiple_choice": "title",
}


def parse_skill_output(execution: SkillExecution) -> None:
    """Parse a completed SkillExecution's output_data into structured models.

    Idempotent: skips if already parsed (parsed_at is set).
    """
    if execution.status != SkillExecutionStatus.COMPLETED:
        return
    if execution.parsed_at is not None:
        return

    parsers = {
        SkillName.ANALYZE_ERRORS: _parse_error_output,
        SkillName.ANALYZE_THEMES: _parse_theme_output,
        SkillName.ANALYZE_LEVEL: _parse_level_output,
        SkillName.GENERATE_QUESTIONS: _parse_question_output,
    }

    parser = parsers.get(execution.skill_name)
    if parser is None:
        logger.debug("No parser for skill %s", execution.skill_name)
        return

    try:
        with transaction.atomic():
            parser(execution)
            execution.parsed_at = timezone.now()
            execution.save(update_fields=["parsed_at", "updated_at"])
        logger.info("Parsed %s output for execution %s", execution.skill_name, execution.id)
    except Exception:
        logger.exception("Failed to parse %s output for execution %s", execution.skill_name, execution.id)
        raise


def parse_all_for_lesson(lesson_id, teacher_id) -> None:
    """Parse all completed but unparsed skill executions for a lesson, in order."""
    executions = SkillExecution.objects.filter(
        lesson_id=lesson_id,
        status=SkillExecutionStatus.COMPLETED,
        parsed_at__isnull=True,
    )

    # Enforce execution order
    order = [
        SkillName.ANALYZE_ERRORS,
        SkillName.ANALYZE_LEVEL,
        SkillName.ANALYZE_THEMES,
        SkillName.GENERATE_QUESTIONS,
    ]
    by_skill = {e.skill_name: e for e in executions}
    for skill_name in order:
        if skill_name in by_skill:
            parse_skill_output(by_skill[skill_name])


# --- Individual parsers ---


def _parse_error_output(execution: SkillExecution) -> None:
    """Parse analyze-lesson-errors output into ErrorRecord + ErrorPattern rows."""
    data = execution.output_data
    errors = data.get("errors", [])
    patterns_data = data.get("error_patterns", [])

    if not errors:
        logger.info("No errors in output for execution %s", execution.id)
        return

    lesson = execution.lesson
    student = execution.student
    teacher = execution.teacher

    # 1. Create ErrorRecord rows
    error_records = []
    for i, error in enumerate(errors):
        l1_transfer_raw = error.get("l1_transfer", False)
        if isinstance(l1_transfer_raw, str):
            l1_is_transfer = l1_transfer_raw.lower().startswith("yes")
            l1_explanation = l1_transfer_raw
        elif isinstance(l1_transfer_raw, bool):
            l1_is_transfer = l1_transfer_raw
            l1_explanation = error.get("l1_transfer_explanation", "")
        else:
            l1_is_transfer = False
            l1_explanation = str(l1_transfer_raw) if l1_transfer_raw else ""

        record = ErrorRecord.objects.create(
            skill_execution=execution,
            lesson=lesson,
            student=student,
            error_type=error.get("type", error.get("error_type", "")),
            error_subtype=error.get("subtype", error.get("error_subtype", "")),
            severity=error.get("severity", ""),
            communicative_impact=error.get("communicative_impact", ""),
            original_text=error.get("original", error.get("original_text", "")),
            corrected_text=error.get("corrected", error.get("corrected_text", "")),
            explanation=error.get("explanation", ""),
            reasoning=error.get("reasoning", ""),
            l1_transfer=l1_is_transfer,
            l1_transfer_explanation=l1_explanation,
            correction_strategy=error.get("correction_strategy", ""),
            utterance_index=error.get("utterance_index"),
            timestamp=error.get("timestamp", error.get("position", {}).get("timestamp", "")),
            source_error_index=error.get("error_index", i + 1),
            exercise_priority=error.get("exercise_priority"),
        )
        error_records.append(record)

    # 2. Create/update ErrorPattern rows from the patterns data
    # The skill output includes an error_patterns array with pattern names and error IDs
    record_by_index = {r.source_error_index: r for r in error_records}

    for pattern_data in patterns_data:
        pattern_name = pattern_data.get("pattern", pattern_data.get("name", ""))
        error_ids = pattern_data.get("error_ids", [])

        if not error_ids or not pattern_name:
            continue

        # Derive pattern_key from the errors in this pattern
        sample_record = record_by_index.get(error_ids[0]) if error_ids else None
        if sample_record:
            pattern_ref = _slugify(pattern_name)
            pattern_key = f"{sample_record.error_type}:{sample_record.error_subtype}:{pattern_ref}"
        else:
            pattern_key = _slugify(pattern_name)

        now = timezone.now()
        pattern, created = ErrorPattern.objects.get_or_create(
            student=student,
            teacher=teacher,
            pattern_key=pattern_key,
            defaults={
                "label": pattern_name,
                "error_type": sample_record.error_type if sample_record else "",
                "error_subtype": sample_record.error_subtype if sample_record else "",
                "status": ErrorPatternStatus.NEW,
                "first_seen_at": now,
                "last_seen_at": now,
                "occurrence_count": len(error_ids),
                "lesson_count": 1,
            },
        )

        if not created:
            # Pattern already exists from a previous lesson
            pattern.occurrence_count += len(error_ids)
            pattern.last_seen_at = now

            # Check if this is a new lesson for this pattern
            existing_lessons = (
                ErrorPatternOccurrence.objects.filter(pattern=pattern).values_list("lesson_id", flat=True).distinct()
            )
            if lesson.id not in set(existing_lessons):
                pattern.lesson_count += 1

            # Update status based on new lesson data
            if pattern.status == ErrorPatternStatus.MASTERED:
                # Mastered but reappearing -> revert to recurring
                pattern.status = ErrorPatternStatus.RECURRING
            elif pattern.lesson_count >= 2 and pattern.status == ErrorPatternStatus.NEW:
                pattern.status = ErrorPatternStatus.RECURRING

            pattern.save(
                update_fields=[
                    "occurrence_count",
                    "last_seen_at",
                    "lesson_count",
                    "status",
                    "updated_at",
                ]
            )

        # 3. Create ErrorPatternOccurrence links
        for error_id in error_ids:
            record = record_by_index.get(error_id)
            if record:
                ErrorPatternOccurrence.objects.get_or_create(
                    pattern=pattern,
                    error_record=record,
                    defaults={"lesson": lesson},
                )

    # Update denormalized counts on TutoringRelationship
    if student and teacher:
        update_tutoring_relationship_counts(teacher.id, student.id)


def _parse_level_output(execution: SkillExecution) -> None:
    """Parse analyze-lesson-level output into LessonLevelAssessment."""
    data = execution.output_data

    overall_level = data.get("level", data.get("overall_level", ""))
    if not overall_level:
        logger.info("No level in output for execution %s", execution.id)
        return

    dimensions = data.get("dimensions", {})
    zpd = data.get("zpd", data.get("zone_of_proximal_development", {}))
    strengths_raw = data.get("strengths", [])
    gaps_raw = data.get("gaps", [])
    suggestions_raw = data.get("suggestions", [])

    # Normalize strengths/gaps: may be strings or dicts with "text" key
    strengths = [s if isinstance(s, str) else s.get("text", str(s)) for s in strengths_raw]
    gaps = [g if isinstance(g, str) else g.get("text", str(g)) for g in gaps_raw]
    suggestions = [s if isinstance(s, str) else s.get("text", str(s)) for s in suggestions_raw]

    LessonLevelAssessment.objects.create(
        skill_execution=execution,
        lesson=execution.lesson,
        student=execution.student,
        overall_level=overall_level,
        range_level=_get_dimension_level(dimensions, "range"),
        accuracy_level=_get_dimension_level(dimensions, "accuracy"),
        fluency_level=_get_dimension_level(dimensions, "fluency"),
        interaction_level=_get_dimension_level(dimensions, "interaction"),
        coherence_level=_get_dimension_level(dimensions, "coherence"),
        strengths=strengths,
        gaps=gaps,
        suggestions=suggestions,
        zpd_lower=zpd.get("lower_bound", zpd.get("lower", "")),
        zpd_upper=zpd.get("upper_bound", zpd.get("upper", "")),
    )

    # Update TutoringRelationship.latest_level
    from apps.tutoring.models import TutoringRelationship

    TutoringRelationship.objects.filter(
        teacher=execution.teacher,
        student=execution.student,
    ).update(
        latest_level=overall_level,
        latest_level_assessed_at=timezone.now(),
    )


def _parse_theme_output(execution: SkillExecution) -> None:
    """Parse analyze-lesson-themes output into LessonTheme rows."""
    data = execution.output_data
    themes = data.get("themes", [])

    if not themes:
        logger.info("No themes in output for execution %s", execution.id)
        return

    for theme in themes:
        transcript_range = theme.get("transcript_range", {})
        if isinstance(transcript_range, str):
            # Parse "00:10 - 02:00" format
            parts = transcript_range.split(" - ") if " - " in transcript_range else [transcript_range, ""]
            range_start, range_end = parts[0], parts[1] if len(parts) > 1 else ""
        else:
            range_start = transcript_range.get("start", "")
            range_end = transcript_range.get("end", "")

        LessonTheme.objects.create(
            skill_execution=execution,
            lesson=execution.lesson,
            student=execution.student,
            topic=theme.get("topic", theme.get("name", "")),
            communicative_function=theme.get("communicative_function", theme.get("function", "")),
            initiated_by=theme.get("initiated_by", ""),
            vocabulary_active=theme.get("vocabulary_active", theme.get("active_vocabulary", [])),
            vocabulary_passive=theme.get("vocabulary_passive", theme.get("passive_vocabulary", [])),
            chunks=theme.get("chunks", []),
            transcript_range_start=range_start,
            transcript_range_end=range_end,
        )


def _parse_question_output(execution: SkillExecution) -> None:
    """Parse generate-classtime-questions output into PracticeQuestion rows.

    Requires that _parse_error_output() has already run for the same lesson
    so that ErrorRecord and ErrorPattern rows exist for linking.
    """
    from apps.classtime_sessions.models import ClasstimeSession, PracticeQuestion

    data = execution.output_data
    questions = data.get("questions", [])

    if not questions:
        logger.info("No questions in output for execution %s", execution.id)
        return

    # Find the ClasstimeSession linked to this skill execution
    session = ClasstimeSession.objects.filter(
        question_skill_execution=execution,
    ).first()

    if session is None:
        # Try to find session by lesson
        session = (
            ClasstimeSession.objects.filter(
                lesson=execution.lesson,
            )
            .order_by("-created_at")
            .first()
        )

    if session is None:
        logger.warning(
            "No ClasstimeSession found for question parsing (execution %s, lesson %s)",
            execution.id,
            execution.lesson_id,
        )
        return

    # Build lookup for ErrorRecord and ErrorPattern linking
    lesson = execution.lesson
    student = execution.student
    teacher = execution.teacher

    error_records_by_index = {}
    if lesson:
        error_records_by_index = {
            r.source_error_index: r for r in ErrorRecord.objects.filter(lesson=lesson, student=student)
        }

    for i, question in enumerate(questions):
        source_ref = question.get("source_ref", {})
        payload_type = question.get("payload_type", "")
        payload = question.get("payload", {})
        difficulty = question.get("difficulty", "")

        # Extract stem based on payload_type
        stem_field = _STEM_FIELD.get(payload_type, "title")
        stem = payload.get(stem_field, payload.get("title", ""))

        # Build source_error_ref for pattern matching
        error_type = source_ref.get("error_type", "")
        subtype = source_ref.get("subtype", "")
        pattern_ref = source_ref.get("pattern_ref", "")
        source_error_ref = f"{error_type}:{subtype}:{pattern_ref}" if pattern_ref else ""

        # Link to ErrorRecord via source_error_index
        error_index = source_ref.get("error_index")
        error_record = error_records_by_index.get(error_index) if error_index else None

        # Link to ErrorPattern via pattern_key
        error_pattern = None
        if source_error_ref and student and teacher:
            error_pattern = ErrorPattern.objects.filter(
                student=student,
                teacher=teacher,
                pattern_key=source_error_ref,
            ).first()

        PracticeQuestion.objects.create(
            session=session,
            error_record=error_record,
            error_pattern=error_pattern,
            question_index=i,
            classtime_question_id="",  # Populated after session creation
            question_type=payload_type,
            difficulty=difficulty,
            stem=stem,
            source_error_ref=source_error_ref,
        )


# --- Helpers ---


def _slugify(name: str) -> str:
    """Convert pattern name to a slug for pattern_key."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def _get_dimension_level(dimensions: dict, key: str) -> str:
    """Extract level from a CEFR dimension entry."""
    dim = dimensions.get(key, {})
    if isinstance(dim, str):
        return dim
    return dim.get("level", "")
