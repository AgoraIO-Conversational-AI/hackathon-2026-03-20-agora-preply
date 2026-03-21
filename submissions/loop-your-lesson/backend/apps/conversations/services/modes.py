"""Agent mode system.

Two modes for MVP: daily_briefing (teacher) and student_practice (student).
"""

from dataclasses import dataclass, field
from enum import StrEnum

import apps.conversations.services.query_tools  # noqa: F401
from apps.conversations.services.prompts import (
    ROLE_STUDENT,
    ROLE_TEACHER,
)
from apps.conversations.services.tools import TOOL_REGISTRY


class AgentMode(StrEnum):
    DAILY_BRIEFING = "daily_briefing"
    STUDENT_PRACTICE = "student_practice"


@dataclass
class ModeConfig:
    name: str
    description: str
    instructions: str
    tool_names: list[str]
    chips: list[str]
    tool_classes: list = field(default_factory=list)


MODE_CONFIGS: dict[str, ModeConfig] = {
    AgentMode.DAILY_BRIEFING: ModeConfig(
        name="daily_briefing",
        description="Teacher reviews student progress and prepares for lessons",
        instructions=ROLE_TEACHER,
        tool_names=[
            "query_daily_overview",
            "query_student_report",
            "query_lesson_errors",
            "query_lesson_themes",
            "create_practice_session",
        ],
        chips=[
            "Show today's overview",
            "How did Maria do?",
            "What should I focus on today?",
        ],
    ),
    AgentMode.STUDENT_PRACTICE: ModeConfig(
        name="student_practice",
        description="Student reviews their lesson analysis and practice results",
        instructions=ROLE_STUDENT,
        tool_names=[
            "query_lesson_errors",
            "query_lesson_themes",
            "create_practice_session",
        ],
        chips=[
            "Show me my errors and set up practice",
            "What should I focus on?",
            "Explain my mistakes",
        ],
    ),
}


def get_mode_config(mode_name: str) -> ModeConfig:
    config = MODE_CONFIGS.get(mode_name)
    if not config:
        config = MODE_CONFIGS[AgentMode.DAILY_BRIEFING]

    config.tool_classes = [TOOL_REGISTRY[name] for name in config.tool_names if name in TOOL_REGISTRY]
    return config
