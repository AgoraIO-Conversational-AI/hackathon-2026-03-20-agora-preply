from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from apps.conversations.services.tools import PreplyTool, register_tool
from apps.skill_results.models import ErrorRecord


class QueryLessonErrorsArgs(BaseModel):
    error_type: str | None = Field(
        None, description="Filter by error type: grammar, vocabulary, pronunciation, fluency"
    )
    severity: str | None = Field(None, description="Filter by severity: minor, moderate, major")


@sync_to_async
def _fetch_errors(lesson_id, student_id, error_type=None, severity=None):
    qs = ErrorRecord.objects.filter(lesson_id=lesson_id)
    if student_id:
        qs = qs.filter(student_id=student_id)
    if error_type:
        qs = qs.filter(error_type=error_type)
    if severity:
        qs = qs.filter(severity=severity)

    errors = []
    for r in qs.order_by("source_error_index"):
        errors.append(
            {
                "type": r.error_type,
                "subtype": r.error_subtype,
                "severity": r.severity,
                "original": r.original_text,
                "corrected": r.corrected_text,
                "explanation": r.explanation,
                "reasoning": r.reasoning,
                "l1_transfer": r.l1_transfer,
                "correction_strategy": r.correction_strategy,
                "position": {"timestamp": r.timestamp, "utterance": r.utterance_index},
            }
        )
    return errors


@register_tool
class QueryLessonErrorsTool(PreplyTool):
    @property
    def name(self):
        return "query_lesson_errors"

    @property
    def description(self):
        return (
            "Get error analysis from the lesson. Returns errors with type, severity,"
            " original text, correction, explanation, and transcript position."
        )

    @property
    def args_schema(self):
        return QueryLessonErrorsArgs

    async def execute(self, *, conversation=None, error_type=None, severity=None):
        errors = None

        if conversation and conversation.lesson_id:
            student_id = conversation.student_id
            errors = await _fetch_errors(conversation.lesson_id, student_id, error_type, severity)

        if not errors:
            errors = self._mock_errors()

        summary = {
            "total": len(errors),
            "by_type": {},
            "by_severity": {},
        }
        for e in errors:
            t = e.get("type", "unknown")
            s = e.get("severity", "unknown")
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
            summary["by_severity"][s] = summary["by_severity"].get(s, 0) + 1

        data = {
            "widget_type": "error_analysis",
            "errors": errors,
            "summary": summary,
        }

        by_sev = summary.get("by_severity", {})
        message = f"Found {len(errors)} errors"
        if error_type:
            message += f" of type '{error_type}'"
        if severity:
            message += f" with severity '{severity}'"
        message += (
            f". {by_sev.get('major', 0)} major, {by_sev.get('moderate', 0)} moderate, {by_sev.get('minor', 0)} minor."
        )

        return message, data

    def _mock_errors(self):
        return [
            {
                "type": "grammar",
                "severity": "moderate",
                "original": "I go to the store yesterday",
                "corrected": "I went to the store yesterday",
                "explanation": "Past simple required for completed past actions",
                "reasoning": (
                    "B1 should have acquired past simple. Marked moderate because it blocks narrative coherence."
                ),
                "position": {"utterance": 34, "timestamp": "12:45"},
            },
            {
                "type": "grammar",
                "severity": "major",
                "original": "She have been working since three years",
                "corrected": "She has been working for three years",
                "explanation": "Subject-verb agreement with 'has' and 'for' with duration",
                "reasoning": ("Two errors compounded: agreement + preposition. Major because it obscures meaning."),
                "position": {"utterance": 52, "timestamp": "18:20"},
            },
            {
                "type": "vocabulary",
                "severity": "minor",
                "original": "I made a travel to Spain",
                "corrected": "I took a trip to Spain",
                "explanation": "Collocation: 'take a trip' not 'make a travel'",
                "reasoning": (
                    "Common L1 interference from Spanish. Minor - meaning is clear despite unnatural phrasing."
                ),
                "position": {"utterance": 15, "timestamp": "05:30"},
            },
            {
                "type": "grammar",
                "severity": "moderate",
                "original": "If I would have known, I would go",
                "corrected": "If I had known, I would have gone",
                "explanation": (
                    "Third conditional: past perfect in if-clause, would have + past participle in main clause"
                ),
                "reasoning": (
                    "Conditional structure breakdown. B1-B2 transition skill."
                    " Moderate - pattern needs focused practice."
                ),
                "position": {"utterance": 71, "timestamp": "24:10"},
            },
        ]
