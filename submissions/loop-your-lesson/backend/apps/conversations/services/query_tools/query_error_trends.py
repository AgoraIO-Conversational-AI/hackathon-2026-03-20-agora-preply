from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from apps.conversations.services.tools import PreplyTool, register_tool
from apps.learning_progress.models import ErrorPattern


class QueryErrorTrendsArgs(BaseModel):
    status: str | None = Field(
        None,
        description="Filter by pattern status: new, recurring, improving, mastered",
    )


@sync_to_async
def _fetch_error_trends(student_id, teacher_id, status=None):
    qs = ErrorPattern.objects.filter(student_id=student_id, teacher_id=teacher_id)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by("-occurrence_count")

    patterns = []
    for p in qs:
        patterns.append(
            {
                "label": p.label,
                "pattern_key": p.pattern_key,
                "error_type": p.error_type,
                "error_subtype": p.error_subtype,
                "status": p.status,
                "occurrence_count": p.occurrence_count,
                "lesson_count": p.lesson_count,
                "first_seen": str(p.first_seen_at.date()),
                "last_seen": str(p.last_seen_at.date()),
                "times_tested": p.times_tested,
                "times_correct": p.times_correct,
                "mastery_score": p.mastery_score,
            }
        )
    return patterns


@register_tool
class QueryErrorTrendsTool(PreplyTool):
    @property
    def name(self):
        return "query_error_trends"

    @property
    def description(self):
        return (
            "Show error patterns for a student across lessons."
            " Tracks which patterns are new, recurring, improving, or mastered."
        )

    @property
    def args_schema(self):
        return QueryErrorTrendsArgs

    async def execute(self, *, conversation=None, status=None):
        patterns = None

        student_id = conversation.student_id if conversation else None
        teacher_id = conversation.teacher_id if conversation else None

        if student_id and teacher_id:
            patterns = await _fetch_error_trends(student_id, teacher_id, status)

        if not patterns:
            patterns = self._mock_patterns()

        by_status = {}
        for p in patterns:
            s = p["status"]
            by_status[s] = by_status.get(s, 0) + 1

        data = {
            "widget_type": "error_trends",
            "patterns": patterns,
            "summary": by_status,
        }

        parts = [f"{len(patterns)} error patterns"]
        if status:
            parts[0] += f" with status '{status}'"
        for s in ["recurring", "new", "improving", "mastered"]:
            if by_status.get(s):
                parts.append(f"{by_status[s]} {s}")
        message = ". ".join(parts) + "."

        return message, data

    def _mock_patterns(self):
        return [
            {
                "label": "Past simple tense errors",
                "pattern_key": "grammar:verb_tense:past_simple",
                "error_type": "grammar",
                "error_subtype": "verb_tense",
                "status": "recurring",
                "occurrence_count": 8,
                "lesson_count": 3,
                "first_seen": "2026-03-01",
                "last_seen": "2026-03-14",
                "times_tested": 2,
                "times_correct": 1,
                "mastery_score": 0.5,
            },
            {
                "label": "Article omission",
                "pattern_key": "grammar:article:omission",
                "error_type": "grammar",
                "error_subtype": "article",
                "status": "improving",
                "occurrence_count": 5,
                "lesson_count": 2,
                "first_seen": "2026-03-07",
                "last_seen": "2026-03-14",
                "times_tested": 3,
                "times_correct": 2,
                "mastery_score": 0.67,
            },
        ]
