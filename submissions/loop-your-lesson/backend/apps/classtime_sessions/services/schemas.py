"""Pydantic schemas for Classtime API payloads.

REST API (questions): DraftJS Struct objects, REST kind values.
Proto API (sessions/results): camelCase, stringified DraftJS.
"""

from __future__ import annotations

import json
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

# --- DraftJS helpers ---
#
# Classtime uses DraftJS for rich text. Two representations:
#   - Struct (dict): REST API content/explanation/choice fields
#   - String (JSON string): Proto API contentDraftjs fields
#
# Inline styles via inlineStyleRanges:
#   {"offset": 0, "length": 4, "style": "BOLD"}
#   Styles: BOLD, ITALIC, UNDERLINE (combinable on same range)
#
# Multiple paragraphs via multiple blocks.
# Use draftjs_rich() for formatted text, draftjs_struct() for plain.


InlineStyle = tuple[int, int, str]  # (offset, length, style)


def draftjs_struct(text: str) -> dict:
    """Plain text DraftJS block (for REST API content fields)."""
    return {
        "blocks": [
            {
                "key": uuid.uuid4().hex[:5],
                "text": text,
                "type": "unstyled",
                "depth": 0,
                "inlineStyleRanges": [],
                "entityRanges": [],
                "data": {},
            }
        ],
        "entityMap": {},
    }


def draftjs_rich(text: str, styles: list[InlineStyle] | None = None) -> dict:
    """DraftJS block with inline formatting.

    Args:
        text: The plain text content.
        styles: List of (offset, length, style) tuples.
            style is one of: "BOLD", "ITALIC", "UNDERLINE".
            Multiple styles can overlap on the same range.

    Example:
        # "went is the correct form"  with "went" bold
        draftjs_rich("went is the correct form", [(0, 4, "BOLD")])

        # "I goed to the store"  with "goed" bold+italic
        draftjs_rich("I goed to the store", [(2, 4, "BOLD"), (2, 4, "ITALIC")])
    """
    ranges = []
    if styles:
        for offset, length, style in styles:
            ranges.append({"offset": offset, "length": length, "style": style})
    return {
        "blocks": [
            {
                "key": uuid.uuid4().hex[:5],
                "text": text,
                "type": "unstyled",
                "depth": 0,
                "inlineStyleRanges": ranges,
                "entityRanges": [],
                "data": {},
            }
        ],
        "entityMap": {},
    }


def draftjs_blocks(paragraphs: list[tuple[str, list[InlineStyle] | None]]) -> dict:
    """Multi-paragraph DraftJS with optional formatting per paragraph.

    Args:
        paragraphs: List of (text, styles) tuples. styles can be None for plain.

    Example:
        draftjs_blocks([
            ("Read the sentence:", None),
            ("'I goed to the store'", [(1, 19, "ITALIC")]),
            ("Is this correct?", [(8, 7, "BOLD")]),
        ])
    """
    blocks = []
    for text, styles in paragraphs:
        ranges = []
        if styles:
            for offset, length, style in styles:
                ranges.append({"offset": offset, "length": length, "style": style})
        blocks.append(
            {
                "key": uuid.uuid4().hex[:5],
                "text": text,
                "type": "unstyled",
                "depth": 0,
                "inlineStyleRanges": ranges,
                "entityRanges": [],
                "data": {},
            }
        )
    return {"blocks": blocks, "entityMap": {}}


def draftjs_bold(text: str) -> dict:
    """Entire text bold."""
    return draftjs_rich(text, [(0, len(text), "BOLD")])


def draftjs_italic(text: str) -> dict:
    """Entire text italic."""
    return draftjs_rich(text, [(0, len(text), "ITALIC")])


def draftjs_string(text: str) -> str:
    """DraftJS as JSON string (for Proto API contentDraftjs fields)."""
    return json.dumps({"blocks": [{"text": text}], "entityMap": {}})


# --- Rich text field helper ---

# Explanation and content fields accept str (auto-wrapped) or dict (pre-built DraftJS)
RichText = str | dict


def _to_draftjs(value: RichText) -> dict:
    """Normalize a RichText value to DraftJS Struct."""
    if isinstance(value, dict):
        return value
    return draftjs_struct(value)


# --- Question payloads (REST format) ---


class BooleanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    is_correct: bool
    explanation: RichText | None = None
    content: RichText | None = None  # optional description shown above the question

    def to_rest_body(self, question_set_id: str) -> dict:
        body: dict = {
            "title": self.title,
            "kind": "bool",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "isCorrect": self.is_correct,
            "categories": [],
            "items": [],
            "clozes": [],
            "choices": [],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


class SingleChoiceOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: RichText  # str or pre-built DraftJS dict
    is_correct: bool = False


class SingleChoicePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    choices: list[SingleChoiceOption]
    explanation: RichText | None = None
    content: RichText | None = None

    def to_rest_body(self, question_set_id: str) -> dict:
        body: dict = {
            "title": self.title,
            "kind": "choice",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "categories": [],
            "items": [],
            "clozes": [],
            "choices": [
                {
                    "id": str(uuid.uuid4()),
                    "content": _to_draftjs(c.text),
                    "image": None,
                    "isCorrect": c.is_correct,
                    "order": i,
                }
                for i, c in enumerate(self.choices)
            ],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


class GapChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    is_correct: bool = False


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["blank", "choices"]
    solution: str = ""  # for blank gaps
    choices: list[GapChoice] = []  # for choices gaps


class GapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    template_text: str  # e.g. "Yesterday I {0} to the store and {1} some milk."
    gaps: list[Gap]
    explanation: RichText | None = None
    content: RichText | None = None

    def to_rest_body(self, question_set_id: str) -> dict:
        # Generate UUIDs for each gap and build gapText with [UUID] placeholders
        gap_ids = [str(uuid.uuid4()) for _ in self.gaps]
        gap_text = self.template_text
        for i, gid in enumerate(gap_ids):
            gap_text = gap_text.replace(f"{{{i}}}", f"[{gid}]")

        rest_gaps = []
        for gap, gid in zip(self.gaps, gap_ids, strict=True):
            if gap.type == "blank":
                rest_gaps.append(
                    {
                        "type": "blank",
                        "gapLocalId": gid,
                        "solution": gap.solution,
                        "choices": [],
                    }
                )
            else:
                rest_gaps.append(
                    {
                        "type": "choices",
                        "gapLocalId": gid,
                        "solution": "",
                        "choices": [
                            {
                                "content": c.content,
                                "isCorrect": c.is_correct,
                                "parentGapLocalId": gid,
                                "index": j,
                            }
                            for j, c in enumerate(gap.choices)
                        ],
                    }
                )

        body: dict = {
            "title": self.title,
            "kind": "gap",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "gapText": gap_text,
            "gaps": rest_gaps,
            "categories": [],
            "items": [],
            "clozes": [],
            "choices": [],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


class SorterPayload(BaseModel):
    """Items listed in CORRECT order. Classtime shuffles for display."""

    model_config = ConfigDict(extra="forbid")

    title: str
    items: list[RichText]  # in correct order; str or DraftJS dict
    explanation: RichText | None = None
    content: RichText | None = None

    def to_rest_body(self, question_set_id: str) -> dict:
        body: dict = {
            "title": self.title,
            "kind": "sorter",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "categories": [],
            "items": [],
            "clozes": [],
            "choices": [
                {
                    "id": str(uuid.uuid4()),
                    "content": _to_draftjs(item),
                    "image": None,
                    "isCorrect": False,
                    "order": i,
                }
                for i, item in enumerate(self.items)
            ],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


class CategorizerItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: RichText  # str or DraftJS dict
    category_index: int  # 0-based index into categories list


class CategorizerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    categories: list[RichText]  # str or DraftJS dict
    items: list[CategorizerItem]
    explanation: RichText | None = None
    content: RichText | None = None

    def to_rest_body(self, question_set_id: str) -> dict:
        cat_ids = [str(uuid.uuid4()) for _ in self.categories]
        body: dict = {
            "title": self.title,
            "kind": "categorizer",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "categories": [
                {"id": cid, "content": _to_draftjs(name)} for cid, name in zip(cat_ids, self.categories, strict=True)
            ],
            "items": [
                {
                    "id": str(uuid.uuid4()),
                    "content": _to_draftjs(item.text),
                    "categories": [cat_ids[item.category_index]],
                }
                for item in self.items
            ],
            "clozes": [],
            "choices": [],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


class MultipleChoicePayload(BaseModel):
    """Student picks multiple correct answers."""

    model_config = ConfigDict(extra="forbid")

    title: str
    choices: list[SingleChoiceOption]  # multiple can be is_correct=True
    explanation: RichText | None = None
    content: RichText | None = None

    def to_rest_body(self, question_set_id: str) -> dict:
        body: dict = {
            "title": self.title,
            "kind": "multiple",
            "weight": 1,
            "isPoll": False,
            "tags": [],
            "isSolutionEmpty": False,
            "categories": [],
            "items": [],
            "clozes": [],
            "choices": [
                {
                    "id": str(uuid.uuid4()),
                    "content": _to_draftjs(c.text),
                    "image": None,
                    "isCorrect": c.is_correct,
                    "order": i,
                }
                for i, c in enumerate(self.choices)
            ],
            "questionSet": question_set_id,
        }
        if self.explanation:
            body["explanation"] = _to_draftjs(self.explanation)
        if self.content:
            body["content"] = _to_draftjs(self.content)
        return body


# Union type for dispatching
QuestionPayload = (
    BooleanPayload | SingleChoicePayload | MultipleChoicePayload | GapPayload | SorterPayload | CategorizerPayload
)


# --- Session presets ---

FeedbackMode = Literal["practice", "after_submit", "reveal_answers"]

FEEDBACK_PRESETS: dict[FeedbackMode, dict] = {
    # Default: right/wrong after each answer, solutions hidden, student retries until correct
    "practice": {
        "resultsSharingSettings": {
            "questionValidation": "ON",
            "solutionWithExplanation": "OFF",
            "answerComment": "OFF",
            "totalScore": "ON",
            "sessionComment": "OFF",
            "pdfExport": "OFF",
        }
    },
    # Answer all first, then see total score. Solutions still hidden.
    "after_submit": {
        "resultsSharingSettings": {
            "questionValidation": "OFF",
            "solutionWithExplanation": "OFF",
            "totalScore": "ON",
            "sessionComment": "ON",
        }
    },
    # Show solutions + explanations (use after student completed, or for review)
    "reveal_answers": {
        "resultsSharingSettings": {
            "questionValidation": "ON",
            "solutionWithExplanation": "ON",
            "answerComment": "ON",
            "totalScore": "ON",
            "sessionComment": "ON",
        }
    },
}


def build_session_settings(
    title: str,
    feedback_mode: FeedbackMode = "practice",
    shuffle_questions: bool = False,
    tts_language: str | None = None,
) -> dict:
    """Build session settings for 1-on-1 tutoring practice."""
    preset = FEEDBACK_PRESETS[feedback_mode]
    settings: dict = {
        "title": title,
        "isActive": True,
        "isConfigured": True,
        "evaluationMode": "PARTIAL_POINTS_WITHOUT_PENALTY",
        "shuffleChoices": True,
        "shuffleQuestions": shuffle_questions,
        "oneAttemptOnly": False,
        "hasReflection": False,
        "forceReflection": False,
        **preset,
    }
    if tts_language:
        settings["defaultTextToSpeechConfig"] = {
            "isEnabled": True,
            "voice": "Female",
            "language": tts_language,
            "speed": 0.9,
        }
    return settings


# --- Response schemas ---


class AnswerSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    answer_id: str
    participant_id: str
    question_id: str
    correctness: str  # CORRECT, WRONG, PARTIALLY_CORRECT, or empty
    points_centis: int
    max_points_centis: int = 0
    gap_results: list[bool] = []  # per-gap correctness
    answered_at: str = ""

    @classmethod
    def from_api(cls, answer: dict, questions: dict | None = None) -> AnswerSummary:
        evaluation = answer.get("evaluation", {})
        gap_evals = evaluation.get("evaluationGap", [])
        points = evaluation.get("gradingPoints", {}).get("pointsCentis", 0)

        max_pts = 0
        if questions:
            q_info = questions.get(answer["questionId"], {}).get("questionInfo", {})
            max_pts = q_info.get("maxPoints", {}).get("pointsCentis", 0)

        return cls(
            answer_id=answer["id"],
            participant_id=answer["participantId"],
            question_id=answer["questionId"],
            correctness=evaluation.get("correctness", "CORRECT" if points > 0 else "WRONG"),
            points_centis=points,
            max_points_centis=max_pts,
            gap_results=[g.get("isCorrect", False) for g in gap_evals],
            answered_at=answer.get("createdAt", ""),
        )
