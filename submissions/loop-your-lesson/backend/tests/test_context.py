"""Tests for the voice practice context builder.

Pure logic tests — no mocking, no DB, no network.
Verifies prompt structure adapts correctly to mastery state and biomarkers.
"""

from services.convoai.context import VoicePracticeContext
from services.convoai.schemas import (
    BiomarkerState,
    ErrorDetail,
    LanguagePair,
    MasteryError,
    MasteryState,
    ThemeDetail,
)


def _make_context() -> VoicePracticeContext:
    """Create a standard test context (Maria, B1, Spanish→English)."""
    return VoicePracticeContext(
        student_name="Maria",
        student_level="B1",
        language_pair=LanguagePair(l1="Spanish", l2="English"),
        errors=[
            ErrorDetail(
                error_type="grammar",
                subtype="articles",
                severity="major",
                original="I go to the school",
                corrected="I go to school",
                explanation="No article before institution nouns",
            ),
            ErrorDetail(
                error_type="grammar",
                subtype="past_tense_irregular",
                severity="moderate",
                original="I goed to the cinema",
                corrected="I went to the cinema",
                explanation="go is irregular",
            ),
        ],
        themes=[
            ThemeDetail(topic="Morning routine", vocabulary=["wake up", "commute"]),
        ],
    )


def _make_mastery() -> MasteryState:
    """Create a mastery state with one quiz result."""
    return MasteryState(
        errors=[
            MasteryError(
                error_type="grammar",
                subtype="articles",
                original="I go to the school",
                corrected="I go to school",
                quiz_result="WRONG",
                quiz_answer="the school",
                focus_level="critical",
            ),
            MasteryError(
                error_type="grammar",
                subtype="past_tense_irregular",
                original="I goed to the cinema",
                corrected="I went to the cinema",
                quiz_result="CORRECT",
                quiz_answer="went",
                focus_level="low",
            ),
        ],
        quiz_events=[
            {"question_id": "q-1", "correctness": "WRONG", "question_title": "Articles"},
            {"question_id": "q-2", "correctness": "CORRECT", "question_title": "Past Tense"},
        ],
        summary={
            "tested": 2,
            "correct": 1,
            "wrong": 1,
            "untested": 0,
            "current_focus": ["articles"],
        },
    )


class TestInitialPrompt:
    def test_contains_all_layers(self) -> None:
        ctx = _make_context()
        prompt = ctx.build_initial_prompt()

        assert "## Role" in prompt
        assert "Maria" in prompt
        assert "## Student Profile" in prompt
        assert "B1" in prompt
        assert "Spanish" in prompt
        assert "## Lesson Errors" in prompt
        assert "articles" in prompt.lower() or "Articles" in prompt
        assert "## Lesson Themes" in prompt
        assert "Morning routine" in prompt
        assert "## Conversation Instructions" in prompt

    def test_errors_show_severity(self) -> None:
        ctx = _make_context()
        prompt = ctx.build_initial_prompt()

        assert "MAJOR" in prompt
        assert "MODERATE" in prompt

    def test_no_errors_shows_message(self) -> None:
        ctx = VoicePracticeContext(
            student_name="Test",
            student_level="A1",
            language_pair=LanguagePair(l1="French", l2="English"),
            errors=[],
            themes=[],
        )
        prompt = ctx.build_initial_prompt()
        assert "No specific errors" in prompt


class TestEnrichedPrompt:
    def test_with_quiz_results(self) -> None:
        ctx = _make_context()
        mastery = _make_mastery()
        prompt = ctx.build_enriched_prompt(mastery)

        assert "## Quiz Results" in prompt
        assert "WRONG" in prompt
        assert "CORRECT" in prompt
        assert "MASTERED" in prompt or "low" in prompt.lower()

    def test_no_quiz_events_omits_section(self) -> None:
        ctx = _make_context()
        mastery = MasteryState(
            errors=[
                MasteryError(
                    error_type="grammar",
                    subtype="articles",
                    original="x",
                    corrected="y",
                ),
            ],
        )
        prompt = ctx.build_enriched_prompt(mastery)

        assert "## Quiz Results" not in prompt

    def test_high_stress_biomarker(self) -> None:
        ctx = _make_context()
        mastery = _make_mastery()
        mastery.biomarkers = BiomarkerState(stress=0.8, exhaustion=0.3)
        prompt = ctx.build_enriched_prompt(mastery)

        assert "Voice Biomarkers" in prompt
        assert "high stress" in prompt.lower() or "stress (0.8)" in prompt

    def test_normal_biomarkers_omits_section(self) -> None:
        ctx = _make_context()
        mastery = _make_mastery()
        mastery.biomarkers = BiomarkerState(stress=0.1, exhaustion=0.1)
        prompt = ctx.build_enriched_prompt(mastery)

        assert "Voice Biomarkers" not in prompt

    def test_exhaustion_biomarker(self) -> None:
        ctx = _make_context()
        mastery = _make_mastery()
        mastery.biomarkers = BiomarkerState(stress=0.2, exhaustion=0.7)
        prompt = ctx.build_enriched_prompt(mastery)

        assert "fatigue" in prompt.lower() or "exhaustion" in prompt.lower()


class TestGreeting:
    def test_contains_student_name(self) -> None:
        ctx = _make_context()
        greeting = ctx.build_greeting()

        assert "Maria" in greeting

    def test_is_friendly(self) -> None:
        ctx = _make_context()
        greeting = ctx.build_greeting()

        assert "Hi" in greeting or "Hello" in greeting


class TestSpeakReaction:
    def test_correct_answer(self) -> None:
        ctx = _make_context()
        text = ctx.format_speak_quiz_reaction("past_tense", is_correct=True)

        assert "past tense" in text.lower()
        assert len(text.encode()) <= 512

    def test_wrong_answer(self) -> None:
        ctx = _make_context()
        text = ctx.format_speak_quiz_reaction("articles", is_correct=False)

        assert "articles" in text.lower()
        assert "practice" in text.lower() or "work on" in text.lower()
        assert len(text.encode()) <= 512
