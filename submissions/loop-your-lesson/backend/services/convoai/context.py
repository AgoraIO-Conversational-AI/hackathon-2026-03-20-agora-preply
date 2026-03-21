"""4-layer context builder for voice practice agent.

Adapts the context injection pattern from docs/deep-dives/05-context-injection.md
for the ConvoAI voice practice agent. Builds system prompts that include:

  Layer 1: Subject context (language pair, L1/L2)
  Layer 2: Student context (name, level, goal)
  Layer 3: Lesson context (full markdown from analysis files)
  Layer 4: Pedagogical context (correction strategy, conversation plan)
  + Live state: quiz results, visual biomarkers
"""

import logging

from services.convoai.schemas import (
    BiomarkerState,
    ErrorDetail,
    LanguagePair,
    LevelSummary,
    MasteryError,
    MasteryState,
    QuizQuestionSummary,
    ThemeDetail,
)

logger = logging.getLogger(__name__)


class VoicePracticeContext:
    """Build and maintain system prompt for voice practice agent."""

    def __init__(
        self,
        student_name: str,
        student_level: str,
        language_pair: LanguagePair,
        errors: list[ErrorDetail],
        themes: list[ThemeDetail],
        questions: list[QuizQuestionSummary] | None = None,
        level_summary: LevelSummary | None = None,
        raw_lesson_context: str = "",
    ) -> None:
        self.student_name = student_name
        self.student_level = student_level
        self.language_pair = language_pair
        self.errors = errors
        self.themes = themes
        self.questions = questions or []
        self.level_summary = level_summary
        self.raw_lesson_context = raw_lesson_context

    def build_initial_prompt(self) -> str:
        """Full system prompt for agent start. All 4 layers, no quiz data yet."""
        sections = [
            self._role_section(),
            self._student_section(),
            self._lesson_context_section(mastery_errors=None),
            self._instructions_section(),
        ]
        return "\n\n".join(s for s in sections if s)

    def build_enriched_prompt(
        self,
        mastery: MasteryState,
    ) -> str:
        """System prompt enriched with live quiz results and visual state.

        Called via /update whenever quiz events or video frames arrive.
        """
        quiz_results_section = self._quiz_results_section(mastery)
        errors_with_mastery = [
            {"subtype": e.subtype, "quiz_result": e.quiz_result, "focus_level": e.focus_level}
            for e in mastery.errors
            if e.quiz_result is not None
        ]
        logger.info(
            "[CONTEXT] build_enriched_prompt: quiz_events=%d errors_with_results=%s quiz_section_empty=%s",
            len(mastery.quiz_events),
            errors_with_mastery or "NONE",
            not quiz_results_section,
        )

        sections = [
            self._role_section(),
            self._student_section(),
            self._lesson_context_section(mastery_errors=mastery.errors),
            quiz_results_section,
            self._biomarker_section(mastery.biomarkers),
            self._instructions_section(),
        ]
        return "\n\n".join(s for s in sections if s)

    def build_greeting(self) -> str:
        """Auto-greeting when student joins the voice channel."""
        return (
            f"Hi {self.student_name}! I'm your speaking practice partner. "
            f"I know we covered some interesting topics in your last lesson — "
            f"let's chat and work on a few things together. Ready?"
        )

    def format_speak_quiz_reaction(self, error_subtype: str, is_correct: bool) -> str:
        """Short text for /speak endpoint on quiz event. Max 512 bytes."""
        if is_correct:
            topic = error_subtype.replace("_", " ")
            return f"Nice work on {topic} in the quiz! You've got that down."
        topic = error_subtype.replace("_", " ")
        return f"I see {topic} came up in the quiz — let's practice that together."

    # --- Private section builders ---

    def _role_section(self) -> str:
        return (
            "## Role\n"
            f"You are {self.student_name}'s {self.language_pair.l2} speaking practice partner.\n"
            "You are warm, patient, and encouraging.\n"
            "You have a natural conversation — you are NOT a quiz or a test."
        )

    def _student_section(self) -> str:
        lines = [
            "## Student Profile",
            f"- Name: {self.student_name}",
            f"- Level: {self.student_level} (CEFR)",
            f"- Native language: {self.language_pair.l1}",
            f"- Learning: {self.language_pair.l2}",
        ]
        return "\n".join(lines)

    def _lesson_context_section(self, mastery_errors: list[MasteryError] | None) -> str:
        """Full lesson context: raw markdown files + live mastery overlay."""
        parts = []

        # Include raw lesson analysis if available (errors, themes, level)
        if self.raw_lesson_context:
            parts.append(
                "## Full Lesson Analysis\n"
                "Below is the complete analysis of the student's last lesson — errors with L1 transfer "
                "explanations, correction strategies, themes with vocabulary, and level assessment. "
                "Use this to understand the student deeply and guide conversation naturally.\n\n"
                + self.raw_lesson_context
            )
        else:
            # Fallback to structured data
            parts.append(self._level_section())
            parts.append(self._errors_section(mastery_errors))
            parts.append(self._questions_section())
            parts.append(self._themes_section())

        # Add live mastery overlay if we have quiz results
        if mastery_errors:
            mastery_overlay = self._mastery_overlay(mastery_errors)
            if mastery_overlay:
                parts.append(mastery_overlay)

        return "\n\n".join(p for p in parts if p)

    def _mastery_overlay(self, mastery_errors: list[MasteryError]) -> str:
        """Live quiz results overlay on top of lesson errors."""
        tested = [e for e in mastery_errors if e.quiz_result is not None]
        if not tested:
            return ""
        lines = ["## Live Quiz Results (overlay on lesson errors)"]
        for err in mastery_errors:
            if err.quiz_result == "CORRECT":
                lines.append(
                    f"- ✓ {err.subtype.replace('_', ' ').title()}: MASTERED in quiz → reduce focus"
                )
            elif err.quiz_result == "WRONG":
                lines.append(
                    f"- ✗ {err.subtype.replace('_', ' ').title()}: WRONG in quiz "
                    f'(wrote "{err.quiz_answer}") → INCREASE focus, create practice scenarios'
                )
        return "\n".join(lines)

    def _errors_section(self, mastery_errors: list[MasteryError] | None) -> str:
        """Fallback errors section when raw_lesson_context is not available."""
        if mastery_errors:
            return self._errors_with_mastery(mastery_errors)
        return self._errors_initial()

    def _errors_initial(self) -> str:
        if not self.errors:
            return "## Lesson Errors\nNo specific errors identified."
        lines = ["## Lesson Errors (from today's lesson)"]
        for i, err in enumerate(self.errors, 1):
            severity_tag = err.severity.upper()
            status_tag = ""
            if err.pattern_status == "recurring":
                status_tag = " [RECURRING]"
            elif err.pattern_status == "mastered":
                status_tag = " [MASTERED]"
            elif err.pattern_status == "improving":
                status_tag = " [IMPROVING]"

            line = (
                f'{i}. [{severity_tag}] {err.subtype.replace("_", " ").title()}: '
                f'said "{err.original}" -> should be "{err.corrected}"{status_tag}'
            )
            if err.l1_transfer and err.l1_transfer_explanation:
                line += f"\n   L1 cause: {err.l1_transfer_explanation[:120]}"
            lines.append(line)
        return "\n".join(lines)

    def _errors_with_mastery(self, mastery_errors: list[MasteryError]) -> str:
        lines = ["## Lesson Errors (with quiz results)"]
        for i, err in enumerate(mastery_errors, 1):
            focus = err.focus_level.upper()
            quiz_status = ""
            if err.quiz_result == "CORRECT":
                quiz_status = " ✓ MASTERED in quiz"
            elif err.quiz_result == "WRONG":
                quiz_status = f' ✗ WRONG in quiz (wrote "{err.quiz_answer}")'

            lines.append(
                f"{i}. [{focus}] {err.subtype.replace('_', ' ').title()}: "
                f'"{err.original}" → "{err.corrected}"{quiz_status}'
            )
        return "\n".join(lines)

    def _themes_section(self) -> str:
        """Fallback themes section when raw_lesson_context is not available."""
        if not self.themes:
            return "## Lesson Themes\nGeneral conversation practice."
        lines = ["## Lesson Themes"]
        for theme in self.themes:
            parts = [f"- {theme.topic}"]
            if theme.communicative_function:
                parts[0] += f" ({theme.communicative_function})"
            active = theme.vocabulary_active or theme.vocabulary[:6]
            if active:
                parts.append(f"  practice: {', '.join(active[:5])}")
            if theme.vocabulary_passive:
                parts.append(f"  expose: {', '.join(theme.vocabulary_passive[:3])}")
            if theme.chunks:
                parts.append(f"  chunks: {', '.join(theme.chunks[:3])}")
            lines.append("\n".join(parts))
        return "\n".join(lines)

    def _quiz_results_section(self, mastery: MasteryState) -> str:
        if not mastery.quiz_events:
            return ""
        lines = ["## Quiz Results (live — updated as student answers)"]
        for event in mastery.quiz_events:
            correctness = event.get("correctness", "UNKNOWN")
            title = event.get("question_title", event.get("question_id", "?"))
            if correctness == "CORRECT":
                lines.append(f"- {title}: CORRECT → reduce focus")
            else:
                lines.append(f"- {title}: WRONG → INCREASE focus")

        # Current priority
        focus = mastery.summary.get("current_focus", [])
        if focus:
            focus_str = ", ".join(str(f) for f in focus)
            lines.append(f"\n## Current Priority\nFocus on: {focus_str}")

        return "\n".join(lines)

    def _biomarker_section(self, biomarkers: BiomarkerState) -> str:
        if biomarkers.stress < 0.3 and biomarkers.exhaustion < 0.3:
            return ""  # Normal state, don't clutter the prompt

        lines = ["## Voice Biomarkers (real-time from Thymia)"]
        if biomarkers.stress > 0.7:
            lines.append(
                f"- Student shows high stress ({biomarkers.stress:.1f}). Speak slowly, "
                "use shorter sentences, offer encouragement before corrections."
            )
        elif biomarkers.stress > 0.4:
            lines.append(f"- Moderate stress ({biomarkers.stress:.1f}). Be patient and encouraging.")

        if biomarkers.exhaustion > 0.6:
            lines.append(
                f"- Student shows fatigue ({biomarkers.exhaustion:.1f}). Consider wrapping up "
                "or switching to easier topics."
            )

        if not lines[1:]:
            lines.append("- Student seems comfortable. Maintain current pace.")

        return "\n".join(lines)

    def _questions_section(self) -> str:
        if not self.questions:
            return ""
        lines = ["## Upcoming Quiz Questions (student is answering these now)"]
        for q in self.questions:
            subtype = q.error_subtype.replace("_", " ")
            lines.append(f"- Q{q.index + 1} [{q.question_type}]: {q.title} (tests: {subtype})")
        lines.append("\nUse this to naturally steer conversation toward these error areas.")
        return "\n".join(lines)

    def _level_section(self) -> str:
        if not self.level_summary:
            return ""
        ls = self.level_summary
        lines = [f"## Level Assessment: {ls.overall_level}"]
        if ls.accuracy_level:
            lines.append(f"- Accuracy: {ls.accuracy_level}, Fluency: {ls.fluency_level}")
        if ls.gaps:
            lines.append(f"- Gaps: {', '.join(ls.gaps[:3])}")
        return "\n".join(lines)

    def _instructions_section(self) -> str:
        return (
            "## Conversation Instructions\n"
            "- Have a natural conversation — NOT a quiz or drill\n"
            "- Weave error practice into the topic naturally\n"
            "- When student makes an error you know about, use RECAST: "
            "repeat what they said correctly without lecturing\n"
            "- Create scenarios that require the focus error patterns\n"
            "- If an error is marked RECURRING, make it a conversation priority\n"
            "- If an error has L1 transfer info, you may briefly explain why it happens\n"
            "- You know the quiz questions — steer conversation to practice those areas\n"
            "- Actively use 'practice' vocabulary; expose student to 'expose' vocabulary in your speech\n"
            "- Keep responses concise (2-3 sentences) — this is spoken conversation\n"
            "- Don't list errors or quiz results to the student\n"
            "- Reference lesson themes and vocabulary naturally in conversation\n"
            "- Use the L1 transfer analysis to anticipate and gently correct errors\n"
            "- If Thymia biomarkers show stress, slow down and encourage\n"
            "- Student is answering a quiz at the same time — don't interrupt their focus, "
            "but naturally reference quiz topics when they come up"
        )
