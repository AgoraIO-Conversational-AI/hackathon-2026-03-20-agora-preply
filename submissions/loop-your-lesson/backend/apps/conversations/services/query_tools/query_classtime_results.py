from collections import Counter

from asgiref.sync import sync_to_async
from pydantic import BaseModel

from apps.classtime_sessions.models import ClasstimeSession, PracticeQuestion, SessionParticipant
from apps.conversations.services.tools import PreplyTool, register_tool


class QueryClasstimeResultsArgs(BaseModel):
    pass


@sync_to_async
def _fetch_practice_data(lesson_id, student_id):
    session = ClasstimeSession.objects.filter(lesson_id=lesson_id).first()
    if not session:
        return None

    # Fetch practice questions with linked errors
    questions = (
        PracticeQuestion.objects.filter(session=session)
        .select_related("error_record")
        .order_by("question_index")
    )

    question_types = dict(Counter(q.question_type for q in questions))
    source_errors = []
    for q in questions:
        if q.error_record:
            source_errors.append({
                "timestamp": q.error_record.timestamp,
                "original": q.error_record.original_text,
            })

    result = {
        "session_code": session.session_code,
        "student_url": session.student_url,
        "question_count": len(questions),
        "question_types": question_types,
        "source_errors": source_errors,
        "session_results": session.results_data,
    }

    # Check participant completion
    completed = False
    if student_id:
        participant = SessionParticipant.objects.filter(session=session, student_id=student_id).first()
        if participant:
            result["participant_results"] = participant.results_data
            completed = participant.completed_at is not None

    result["completed"] = completed
    return result


@register_tool
class QueryClasstimeResultsTool(PreplyTool):
    @property
    def name(self):
        return "query_classtime_results"

    @property
    def description(self):
        return (
            "Get practice session results. If no session exists, use create_practice_session instead. "
            "If practice is not yet completed, returns a practice card. If completed, shows results."
        )

    @property
    def args_schema(self):
        return QueryClasstimeResultsArgs

    async def execute(self, *, conversation=None):
        if not conversation or not conversation.lesson_id:
            return "No lesson context. Use create_practice_session to create a new session.", {}

        db_data = await _fetch_practice_data(
            conversation.lesson_id,
            conversation.student_id,
        )

        if db_data is None:
            return (
                "No practice session exists for this lesson yet. "
                "Use the create_practice_session tool to create one.",
                {},
            )

        completed = db_data.get("completed", False)

        if not completed:
            return self._build_practice_card(db_data)
        return self._build_practice_results(db_data)

    def _build_practice_card(self, db_data):
        """Return practice_card widget with 'Start practice' button."""
        data = {
            "widget_type": "practice_card",
            "question_count": db_data.get("question_count", 0),
            "question_types": db_data.get("question_types", {}),
            "focus_topic": "Lesson errors",
            "source_errors": db_data.get("source_errors", []),
            "session_url": db_data.get("student_url", ""),
        }

        message = (
            f"Practice session ready with {data['question_count']} exercises. "
            "Click 'Start practice' to begin."
        )
        return message, data

    def _build_practice_results(self, db_data):
        """Return practice_results widget with completed scores."""
        participant_data = db_data.get("participant_results", {})
        questions = participant_data.get("questions", [])
        score = participant_data.get("score")

        total = participant_data.get("total", len(questions) if questions else 0)
        percentage = participant_data.get("percentage", round(score / total * 100) if score and total else 0)

        data = {
            "widget_type": "practice_results",
            "session_code": db_data.get("session_code", ""),
            "completed": True,
            "score": score,
            "total": total,
            "percentage": percentage,
            "questions": questions,
        }

        if questions:
            correct = sum(1 for q in questions if q.get("correct"))
            total_q = len(questions)
            message = f"Practice results: {correct}/{total_q} correct ({percentage}%)."
        else:
            message = f"Practice completed with score {score}%."

        return message, data
