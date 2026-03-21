"""Question set and question creation via Classtime REST API.

Uses REST API (api.classtime.com/teachers-api/v2/) for all question types
except CLOZE which falls back to Proto API.
"""

from __future__ import annotations

import logging

from django.conf import settings

from .client import rest_get, rest_get_as, rest_post, rest_post_as
from .schemas import QuestionPayload

logger = logging.getLogger(__name__)


def create_question_set(
    title: str,
    folder_id: str | None = None,
    token: str | None = None,
) -> str:
    """Create a question set in the teacher's library. Returns question_set_id (UUID)."""
    body: dict = {"title": title}
    if folder_id:
        body["parent"] = folder_id
    elif settings.CLASSTIME_FOLDER_ID:
        body["parent"] = settings.CLASSTIME_FOLDER_ID
    resp = rest_post_as(token, "question-sets/", body) if token else rest_post("question-sets/", body)
    qs_id = resp["id"]
    logger.info("Created question set %s: %s", qs_id, title)
    return qs_id


def create_question(
    question_set_id: str,
    payload: QuestionPayload,
    token: str | None = None,
) -> str:
    """Create a question in a question set. Returns question_id (UUID)."""
    body = payload.to_rest_body(question_set_id)
    resp = rest_post_as(token, "questions/", body) if token else rest_post("questions/", body)
    q_id = resp["id"]
    logger.info("Created %s question %s in QS %s", body["kind"], q_id, question_set_id)
    return q_id


def create_questions_batch(
    question_set_id: str,
    payloads: list[QuestionPayload],
    token: str | None = None,
) -> list[str]:
    """Create multiple questions. Returns list of question_ids."""
    return [create_question(question_set_id, p, token=token) for p in payloads]


def get_question_set(question_set_id: str, token: str | None = None) -> dict:
    """Get question set details including question list."""
    path = f"question-sets/{question_set_id}/"
    return rest_get_as(token, path) if token else rest_get(path)


def list_question_sets(token: str | None = None) -> list[dict]:
    """List all question sets in the teacher's library."""
    return rest_get_as(token, "question-sets/") if token else rest_get("question-sets/")
