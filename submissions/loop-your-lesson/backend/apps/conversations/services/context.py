"""Context injection for system prompt building."""

from __future__ import annotations

from typing import Any

from apps.conversations.services.context_types import ConversationContext
from apps.conversations.services.modes import AgentMode
from apps.conversations.services.prompts import (
    CONSTRAINTS_SHARED,
    CONSTRAINTS_STUDENT,
    CONSTRAINTS_TEACHER,
    FORMATTING,
    ROLE_STUDENT,
    ROLE_TEACHER,
    TONE,
    TOOLS_STUDENT_DEFAULT,
    TOOLS_STUDENT_WITH_TRANSCRIPT,
    TOOLS_TEACHER,
    get_subject_prompt,
)
from apps.skill_results.models import SkillName


def build_system_prompt(mode: str, context: ConversationContext | None = None) -> str:
    """Build the system prompt for the agent loop.

    Static prefix first (prompt caching), dynamic suffix last.
    """
    is_student = mode == AgentMode.STUDENT_PRACTICE
    parts: list[str] = []

    # Static prefix (cacheable)
    parts.append(ROLE_STUDENT if is_student else ROLE_TEACHER)
    parts.append(TONE)
    parts.append(FORMATTING)
    parts.append(CONSTRAINTS_SHARED)
    parts.append(CONSTRAINTS_STUDENT if is_student else CONSTRAINTS_TEACHER)

    # Subject-aware sections (from registry)
    subject = (context or {}).get("subject", {})
    subject_prompt = get_subject_prompt(
        subject.get("subject_type", "language"),
        subject.get("subject_config", {}),
        mode,
    )
    parts.append(subject_prompt.pedagogical)
    parts.append(subject_prompt.communication)

    # Dynamic context sections
    if context:
        student = context.get("student")
        if student and student.get("student_name"):
            parts.append(
                f"<context>\n"
                f"- Name: {student['student_name']}\n"
                f"- Level: {student.get('level', 'unknown')}\n"
                f"- Goal: {student.get('goal', '')}\n"
                f"{subject_prompt.subject_line}\n"
                f"</context>"
            )

        teacher = context.get("teacher")
        if teacher and teacher.get("teacher_name"):
            parts.append(
                f"<teacher>\n"
                f"- Name: {teacher['teacher_name']}\n"
                f"- Students today: {teacher.get('student_count', 0)}\n"
                f"</teacher>"
            )

        lesson = context.get("lesson")
        if lesson and lesson.get("lesson_date"):
            parts.append(
                f"<lesson>\n"
                f"- Date: {lesson['lesson_date']}\n"
                f"- Duration: {lesson.get('duration', '')} minutes\n"
                f"- Summary: {lesson.get('summary', '')}\n"
                f"</lesson>"
            )

        if lesson and lesson.get("transcript"):
            formatted = _format_transcript(lesson["transcript"])
            if formatted:
                parts.append(formatted)

        if lesson and lesson.get("skill_outputs"):
            formatted = _format_skill_outputs(lesson["skill_outputs"])
            if formatted:
                parts.append(formatted)

    # Tools section (depends on mode + transcript presence)
    has_transcript = bool(context and context.get("lesson", {}).get("transcript"))
    parts.append(_get_tools_section(mode, has_transcript))

    return "\n\n".join(p for p in parts if p)


def _get_tools_section(mode: str, has_transcript: bool) -> str:
    if mode == AgentMode.STUDENT_PRACTICE:
        return TOOLS_STUDENT_WITH_TRANSCRIPT if has_transcript else TOOLS_STUDENT_DEFAULT
    return TOOLS_TEACHER


def _format_transcript(transcript: dict[str, Any]) -> str | None:
    """Format lesson transcript as readable conversation."""
    utterances = transcript.get("utterances", [])
    if not utterances:
        return None
    lines = [f"[{u.get('timestamp', '')}] {u.get('speaker', '')}: {u.get('text', '')}" for u in utterances]
    return "\n\n## Lesson transcript\n" + "\n".join(lines)


def _format_skill_outputs(outputs: dict[str, Any]) -> str | None:
    """Format skill execution outputs as markdown sections."""
    sections: list[str] = []

    errors_data = outputs.get(SkillName.ANALYZE_ERRORS)
    if errors_data:
        error_lines = [
            f'  - [{e.get("severity")}] "{e.get("original")}" -> "{e.get("corrected")}" ({e.get("explanation")})'
            for e in errors_data.get("errors", [])
        ]
        if error_lines:
            sections.append("### Error analysis\n" + "\n".join(error_lines))

    themes_data = outputs.get(SkillName.ANALYZE_THEMES)
    if themes_data:
        theme_lines = [
            f"  - {t.get('topic')}: {', '.join(t.get('vocabulary', []))}" for t in themes_data.get("themes", [])
        ]
        if theme_lines:
            sections.append("### Themes covered\n" + "\n".join(theme_lines))

    level_data = outputs.get(SkillName.ANALYZE_LEVEL)
    if level_data:
        level_lines = [f"Level: {level_data.get('level')} ({level_data.get('framework', 'CEFR')})"]
        if level_data.get("strengths"):
            level_lines.append("Strengths: " + "; ".join(level_data["strengths"]))
        if level_data.get("gaps"):
            level_lines.append("Gaps: " + "; ".join(level_data["gaps"]))
        sections.append("### Level assessment\n" + "\n".join(level_lines))

    if not sections:
        return None
    return "\n\n## Lesson analysis results\n" + "\n\n".join(sections)
