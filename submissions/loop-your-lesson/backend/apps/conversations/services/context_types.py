"""Typed context definitions for conversation modes.

Each TypedDict represents a section of context injected into the system prompt.
All fields are optional (total=False) since context is built incrementally.
"""

from typing import Any, TypedDict

__all__ = [
    "StudentContext",
    "LessonContext",
    "TeacherContext",
    "SubjectContext",
    "ConversationContext",
]


class StudentContext(TypedDict, total=False):
    student_name: str
    level: str
    goal: str


class LessonContext(TypedDict, total=False):
    lesson_date: str
    duration: int
    summary: str
    transcript: dict[str, Any]  # {"utterances": [{"speaker", "text", "timestamp"}]}
    skill_outputs: dict[str, Any]  # {skill_name: output_data}


class TeacherContext(TypedDict, total=False):
    teacher_name: str
    student_count: int


class SubjectContext(TypedDict, total=False):
    """Opaque subject pass-through from TutoringRelationship/Lesson.

    The raw subject_config flows through unchanged - prompt builders
    in the subject registry interpret it per subject_type.
    """

    subject_type: str  # "language", "math", "music"
    subject_config: dict[str, Any]  # Raw JSON, opaque pass-through


class ConversationContext(TypedDict, total=False):
    """Top-level context passed to build_system_prompt().

    Built in chat_agent.py from conversation's related objects.
    Each section is independently optional.
    """

    student: StudentContext
    lesson: LessonContext
    teacher: TeacherContext
    subject: SubjectContext
