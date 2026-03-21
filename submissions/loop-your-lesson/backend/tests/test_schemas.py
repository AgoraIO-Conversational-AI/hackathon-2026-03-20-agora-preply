"""Tests for Pydantic schema validation.

Verifies extra="forbid" works, required fields are enforced,
and default values behave correctly.
"""

import pytest
from pydantic import ValidationError

from services.convoai.schemas import (
    BiomarkerState,
    ErrorDetail,
    MasteryError,
    MasteryState,
    VoiceSessionStart,
)


class TestVoiceSessionStart:
    def test_valid(self) -> None:
        s = VoiceSessionStart(student_id="abc", lesson_id="def")
        assert s.student_id == "abc"
        assert s.classtime_session_code is None

    def test_with_classtime_code(self) -> None:
        s = VoiceSessionStart(student_id="abc", lesson_id="def", classtime_session_code="XYZ123")
        assert s.classtime_session_code == "XYZ123"

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            VoiceSessionStart(student_id="abc", lesson_id="def", sneaky="value")

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            VoiceSessionStart(student_id="abc")  # type: ignore[call-arg]


class TestErrorDetail:
    def test_all_fields_required(self) -> None:
        with pytest.raises(ValidationError):
            ErrorDetail(error_type="grammar")  # type: ignore[call-arg]

    def test_valid(self) -> None:
        e = ErrorDetail(
            error_type="grammar",
            subtype="articles",
            severity="major",
            original="the school",
            corrected="school",
            explanation="no article",
        )
        assert e.subtype == "articles"


class TestMasteryState:
    def test_defaults(self) -> None:
        m = MasteryState(errors=[])
        assert m.quiz_events == []
        assert m.summary == {}
        assert m.biomarkers.stress == 0.0
        assert m.biomarkers.exhaustion == 0.0

    def test_with_errors(self) -> None:
        m = MasteryState(
            errors=[
                MasteryError(
                    error_type="grammar",
                    subtype="articles",
                    original="x",
                    corrected="y",
                ),
            ]
        )
        assert len(m.errors) == 1
        assert m.errors[0].quiz_result is None
        assert m.errors[0].focus_level == "high"


class TestBiomarkerState:
    def test_defaults_zero(self) -> None:
        b = BiomarkerState()
        assert b.stress == 0.0
        assert b.exhaustion == 0.0
        assert b.distress == 0.0

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            BiomarkerState(stress=0.5, happiness=0.8)  # type: ignore[call-arg]
