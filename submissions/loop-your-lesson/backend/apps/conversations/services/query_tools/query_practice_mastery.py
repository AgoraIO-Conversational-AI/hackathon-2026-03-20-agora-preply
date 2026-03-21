from asgiref.sync import sync_to_async
from pydantic import BaseModel

from apps.classtime_sessions.models import PracticeQuestion, PracticeResult
from apps.conversations.services.tools import PreplyTool, register_tool
from apps.learning_progress.models import ErrorPattern


class QueryPracticeMasteryArgs(BaseModel):
    pass


@sync_to_async
def _fetch_practice_mastery(student_id, teacher_id):
    """Get mastery data: which patterns were tested and how they scored."""
    patterns = ErrorPattern.objects.filter(
        student_id=student_id,
        teacher_id=teacher_id,
        times_tested__gt=0,
    ).order_by("-times_tested")

    results = []
    for p in patterns:
        # Get individual question results for this pattern
        questions = PracticeQuestion.objects.filter(error_pattern=p)
        question_details = []
        for q in questions:
            result = PracticeResult.objects.filter(practice_question=q).first()
            if result:
                question_details.append(
                    {
                        "question_type": q.question_type,
                        "difficulty": q.difficulty,
                        "stem": q.stem[:80],
                        "is_correct": result.is_correct,
                        "student_answer": result.student_answer,
                    }
                )

        results.append(
            {
                "pattern": p.label,
                "status": p.status,
                "times_tested": p.times_tested,
                "times_correct": p.times_correct,
                "mastery_score": p.mastery_score,
                "questions": question_details,
            }
        )

    return results


@register_tool
class QueryPracticeMasteryTool(PreplyTool):
    @property
    def name(self):
        return "query_practice_mastery"

    @property
    def description(self):
        return (
            "Show which error patterns were tested in practice and the mastery status."
            " Includes per-question results linked back to original errors."
        )

    @property
    def args_schema(self):
        return QueryPracticeMasteryArgs

    async def execute(self, *, conversation=None):
        results = None

        student_id = conversation.student_id if conversation else None
        teacher_id = conversation.teacher_id if conversation else None

        if student_id and teacher_id:
            results = await _fetch_practice_mastery(student_id, teacher_id)

        if not results:
            results = self._mock_mastery()

        mastered = sum(1 for r in results if r["status"] == "mastered")
        improving = sum(1 for r in results if r["status"] == "improving")
        struggling = sum(1 for r in results if r["status"] in ("new", "recurring"))

        data = {
            "widget_type": "practice_mastery",
            "patterns": results,
            "summary": {
                "total_tested": len(results),
                "mastered": mastered,
                "improving": improving,
                "struggling": struggling,
            },
        }

        message = (
            f"{len(results)} patterns tested. {mastered} mastered, {improving} improving, {struggling} need more work."
        )
        return message, data

    def _mock_mastery(self):
        return [
            {
                "pattern": "Past simple tense errors",
                "status": "improving",
                "times_tested": 4,
                "times_correct": 3,
                "mastery_score": 0.75,
                "questions": [
                    {
                        "question_type": "gap",
                        "difficulty": "zpd_target",
                        "stem": "Yesterday she ___ to the store.",
                        "is_correct": True,
                        "student_answer": "went",
                    },
                ],
            },
            {
                "pattern": "Article omission",
                "status": "mastered",
                "times_tested": 5,
                "times_correct": 5,
                "mastery_score": 1.0,
                "questions": [],
            },
        ]
