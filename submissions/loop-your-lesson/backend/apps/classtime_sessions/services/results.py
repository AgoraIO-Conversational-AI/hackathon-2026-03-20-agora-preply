"""Classtime result sync, answer querying, feedback, and export.

All via Proto API. Results are normalized into AnswerSummary schemas.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant

from .client import proto_call
from .schemas import AnswerSummary

logger = logging.getLogger(__name__)

# Session status constants
STATUS_CREATED = "created"
STATUS_COMPLETED = "completed"

# Correctness constants (from Classtime Proto API)
CORRECTNESS_CORRECT = "CORRECT"
CORRECTNESS_PARTIALLY_CORRECT = "PARTIALLY_CORRECT"
CORRECTNESS_WRONG = "WRONG"

# Comment state constants
COMMENT_SAVED = "SAVED"
COMMENT_DRAFT = "DRAFT"


def get_answers_summary(session_code: str) -> list[AnswerSummary]:
    """Get all answers with evaluations for a session.

    Enriches with question info (max points, kind) when available.
    """
    summary_resp = proto_call(
        "Session",
        "getAnswersSummary",
        {
            "sessionCode": session_code,
        },
    )
    answers = summary_resp.get("answers", [])
    if not answers:
        return []

    details = proto_call("Session", "getSessionDetails", {"code": session_code})
    questions = details.get("questions", {})

    return [AnswerSummary.from_api(a, questions) for a in answers]


def get_detailed_answers(session_code: str, question_id: str) -> list[dict]:
    """Get what students actually submitted for a specific question.

    Returns the raw answer content (answerBoolean, answerGap, etc.)
    plus evaluation.
    """
    resp = proto_call(
        "Session",
        "getAnswers",
        {
            "sessionCode": session_code,
            "questionId": question_id,
        },
    )
    return resp.get("answerInfos", [])


def suggest_comment(session_code: str, answer_id: str) -> str | None:
    """Get AI-suggested feedback for an answer (Slate JSON).

    Returns None if the question type doesn't support it (e.g., BOOLEAN).
    """
    try:
        resp = proto_call(
            "Session",
            "suggestComment",
            {
                "sessionCode": session_code,
                "answerId": answer_id,
            },
        )
        return resp.get("commentInfo", {}).get("comment", {}).get("content")
    except Exception:
        logger.debug("suggestComment failed for %s (may be unsupported type)", answer_id)
        return None


def save_comment(
    session_code: str,
    participant_id: str,
    question_id: str,
    answer_id: str,
    text: str,
    state: str = COMMENT_SAVED,
) -> str | None:
    """Save a teacher comment on an answer.

    Content must be Slate JSON format. Plain text is auto-wrapped.
    Returns comment_id.
    """
    content = json.dumps([{"children": [{"text": text}], "type": "paragraph"}]) if not text.startswith("[") else text

    resp = proto_call(
        "Session",
        "createOrUpdateComments",
        {
            "sessionCode": session_code,
            "commentInfos": [
                {
                    "participantId": participant_id,
                    "comment": {
                        "state": state,
                        "content": content,
                        "questionRef": {"id": question_id},
                        "answerRef": {"id": answer_id},
                    },
                }
            ],
        },
    )
    comment_ids = resp.get("commentIds", [])
    return comment_ids[0] if comment_ids else None


def export_session(session_code: str, report_type: str = "INSIGHTS_XLSX") -> str:
    """Export session results. Returns download URL."""
    resp = proto_call(
        "Session",
        "exportSession",
        {
            "sessionCode": session_code,
            "type": report_type,
        },
    )
    return resp["exportLink"]


# --- Sync results from Classtime to our DB ---


def sync_session_results(session: ClasstimeSession) -> dict:
    """Fetch results from Classtime and store in our DB.

    Populates session.results_data and participant.results_data with
    normalized question-level results linked to source errors.
    """
    code = session.session_code

    # 1. Get answer summary and session details from Classtime
    summary_resp = proto_call("Session", "getAnswersSummary", {"sessionCode": code})
    raw_answers = summary_resp.get("answers", [])

    if not raw_answers:
        logger.info("No answers yet for session %s", code)
        return {"answers": 0}

    details = proto_call("Session", "getSessionDetails", {"code": code})
    ct_questions = details.get("questions", {})

    # 2. Build source_ref mapping: session question_id -> source error
    # questions_data stores library IDs; session uses different IDs.
    # Map via derivedFromQuestionRef in session details.
    lib_to_source = {qd.get("question_id"): qd for qd in (session.questions_data or [])}
    session_to_source = {}
    for ct_qid, ct_q in ct_questions.items():
        lib_id = ct_q.get("derivedFromQuestionRef", {}).get("id")
        if lib_id and lib_id in lib_to_source:
            session_to_source[ct_qid] = lib_to_source[lib_id]

    # 3. Get detailed answers for each question
    answered_qids = {a["questionId"] for a in raw_answers}
    detailed_by_answer = {}
    for qid in answered_qids:
        try:
            resp = proto_call(
                "Session",
                "getAnswers",
                {
                    "sessionCode": code,
                    "questionId": qid,
                },
            )
            for ai in resp.get("answerInfos", []):
                aid = ai.get("answerId") or ai.get("answer_id", "")
                detailed_by_answer[aid] = ai
        except Exception:
            logger.debug("Failed to get detailed answer for %s/%s", code, qid)

    # 4. Build per-question results
    question_results = _build_question_results(
        raw_answers,
        ct_questions,
        session_to_source,
        detailed_by_answer,
    )

    # 5. Compute summary
    correct_count = sum(1 for q in question_results if q["correct"])
    total = len(question_results)
    points_earned = sum(q["points"] for q in question_results)
    points_possible = sum(q["max_points"] for q in question_results)
    percentage = round(correct_count / total * 100) if total else 0
    now = datetime.now(UTC).isoformat()

    participant_results = {
        "score": correct_count,
        "total": total,
        "percentage": percentage,
        "points_earned": points_earned,
        "points_possible": points_possible,
        "synced_at": now,
        "questions": question_results,
    }

    session_summary = {
        "total_participants": 1,
        "total_questions": total,
        "total_points": points_possible,
        "synced_at": now,
        "raw_answers": raw_answers,
    }

    # 6. Store in DB
    session.results_data = session_summary
    session.results_synced_at = datetime.now(UTC)
    session.status = STATUS_COMPLETED
    session.save(update_fields=["results_data", "results_synced_at", "status", "updated_at"])

    participant = SessionParticipant.objects.filter(session=session).first()
    if participant:
        participant.results_data = participant_results
        participant.completed_at = datetime.now(UTC)
        participant.save(update_fields=["results_data", "completed_at", "updated_at"])

        # Create PracticeResult rows and update ErrorPattern mastery
        _create_practice_results(participant, question_results)

    logger.info(
        "Synced results for session %s: %d/%d correct (%d%%)",
        code,
        correct_count,
        total,
        percentage,
    )
    return participant_results


def _build_question_results(
    raw_answers: list[dict],
    ct_questions: dict,
    session_to_source: dict,
    detailed_by_answer: dict,
) -> list[dict]:
    """Build normalized per-question results from Classtime API data."""
    results = []
    for answer in raw_answers:
        qid = answer["questionId"]
        evaluation = answer.get("evaluation", {})
        points = evaluation.get("gradingPoints", {}).get("pointsCentis", 0)
        gap_evals = evaluation.get("evaluationGap", [])
        correctness = evaluation.get("correctness", "")
        if not correctness:
            correctness = CORRECTNESS_CORRECT if points > 0 else CORRECTNESS_WRONG

        q_info = ct_questions.get(qid, {}).get("questionInfo", {})
        max_pts = q_info.get("maxPoints", {}).get("pointsCentis", 0)
        kind = q_info.get("kind", "")
        title = q_info.get("title", "")

        student_answer = _extract_student_answer(detailed_by_answer.get(answer["id"], {}))
        source = session_to_source.get(qid, {})

        results.append(
            {
                "question_id": qid,
                "question_title": title,
                "question_type": kind.lower() if kind else "",
                "correct": correctness == CORRECTNESS_CORRECT,
                "points": points,
                "max_points": max_pts,
                "student_answer": student_answer,
                "expected": "",
                "gap_results": [g.get("isCorrect", False) for g in gap_evals],
                "source_error": source.get("source_ref"),
            }
        )
    return results


def _extract_student_answer(detail: dict) -> str:
    """Extract what the student typed/selected from a detailed answer."""
    raw_answer = detail.get("answer", {})
    for key, val in raw_answer.items():
        if not key.startswith("answer"):
            continue
        if not isinstance(val, dict):
            continue
        if "content" in val:
            return val["content"]
        if "isTrue" in val:
            return str(val["isTrue"])
        if "selectedChoice" in val:
            return str(val["selectedChoice"])
        if "gaps" in val:
            parts = []
            for g in val["gaps"]:
                parts.append(g.get("content", str(g.get("choiceIndex", ""))))
            return ", ".join(parts)
        if "sortedChoices" in val:
            return str(val["sortedChoices"])
        if "selectedCategories" in val:
            return str(val["selectedCategories"])
    return ""


def _create_practice_results(
    participant: SessionParticipant,
    question_results: list[dict],
) -> None:
    """Create PracticeResult rows from synced results and update ErrorPattern mastery."""
    from apps.classtime_sessions.models import PracticeQuestion, PracticeResult
    from apps.learning_progress.services import update_mastery_after_result

    session = participant.session

    # Build lookup: classtime_question_id -> PracticeQuestion
    practice_questions = {
        pq.classtime_question_id: pq
        for pq in PracticeQuestion.objects.filter(session=session)
        if pq.classtime_question_id
    }

    if not practice_questions:
        logger.debug("No PracticeQuestion rows found for session %s", session.session_code)
        return

    for result in question_results:
        ct_question_id = result.get("question_id", "")
        pq = practice_questions.get(ct_question_id)
        if pq is None:
            continue

        practice_result, created = PracticeResult.objects.get_or_create(
            participant=participant,
            practice_question=pq,
            defaults={
                "is_correct": result.get("correct", False),
                "student_answer": result.get("student_answer", ""),
                "answered_at": datetime.now(UTC),
            },
        )

        if created and pq.error_pattern:
            update_mastery_after_result(pq.error_pattern, practice_result.is_correct)
