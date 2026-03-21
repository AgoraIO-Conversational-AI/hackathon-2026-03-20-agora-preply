from apps.conversations.services.context import build_system_prompt
from apps.conversations.services.prompts import (
    TOOLS_STUDENT_DEFAULT,
    TOOLS_STUDENT_WITH_TRANSCRIPT,
    TOOLS_TEACHER,
)
from apps.skill_results.models import SkillName


class TestBuildSystemPrompt:
    def test_daily_briefing_basic(self):
        prompt = build_system_prompt("daily_briefing")
        assert "teacher" in prompt.lower()
        assert "<role>" in prompt

    def test_student_practice_basic(self):
        prompt = build_system_prompt("student_practice")
        assert "student" in prompt.lower()
        assert "<role>" in prompt

    def test_with_student_context(self):
        context = {"student": {"student_name": "Maria", "level": "B1", "goal": "Fluency"}}
        prompt = build_system_prompt("student_practice", context=context)
        assert "Maria" in prompt
        assert "B1" in prompt
        assert "Fluency" in prompt

    def test_with_lesson_context(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "duration": 50,
                "summary": "Travel planning lesson",
            }
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "2026-03-14" in prompt
        assert "50" in prompt
        assert "Travel planning" in prompt

    def test_with_teacher_context(self):
        context = {"teacher": {"teacher_name": "John", "student_count": 5}}
        prompt = build_system_prompt("daily_briefing", context=context)
        assert "John" in prompt
        assert "5" in prompt

    def test_pedagogical_context_always_present(self):
        prompt = build_system_prompt("daily_briefing")
        assert "CEFR" in prompt
        assert "grammar" in prompt

    def test_unknown_mode_falls_back_to_daily_briefing(self):
        prompt = build_system_prompt("nonexistent_mode")
        assert "teacher" in prompt.lower()


class TestPromptStructure:
    def test_xml_tags_present(self):
        prompt = build_system_prompt("daily_briefing")
        for tag in [
            "<role>",
            "<tone>",
            "<formatting>",
            "<constraints>",
            "<pedagogical>",
            "<communication>",
            "<tools>",
        ]:
            assert tag in prompt, f"Missing tag: {tag}"

    def test_constraints_always_present(self):
        for mode in ["daily_briefing", "student_practice"]:
            prompt = build_system_prompt(mode)
            assert "NEVER start with" in prompt
            assert "NEVER lecture" in prompt

    def test_teacher_mode_has_teacher_constraints(self):
        prompt = build_system_prompt("daily_briefing")
        assert "<constraints_teacher>" in prompt
        assert "<constraints_student>" not in prompt

    def test_student_mode_has_student_constraints(self):
        prompt = build_system_prompt("student_practice")
        assert "<constraints_student>" in prompt
        assert "<constraints_teacher>" not in prompt


class TestToolsSections:
    def test_teacher_mode_uses_teacher_tools(self):
        prompt = build_system_prompt("daily_briefing")
        assert TOOLS_TEACHER in prompt

    def test_student_with_transcript_uses_transcript_tools(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "transcript": {"utterances": [{"speaker": "T", "text": "Hi", "timestamp": "00:00"}]},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert TOOLS_STUDENT_WITH_TRANSCRIPT in prompt
        assert TOOLS_STUDENT_DEFAULT not in prompt

    def test_student_without_transcript_uses_default_tools(self):
        prompt = build_system_prompt("student_practice")
        assert TOOLS_STUDENT_DEFAULT in prompt
        assert TOOLS_STUDENT_WITH_TRANSCRIPT not in prompt


class TestTranscriptInjection:
    def test_transcript_included_in_prompt(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "transcript": {
                    "utterances": [
                        {
                            "speaker": "Teacher",
                            "text": "How are you?",
                            "timestamp": "00:15",
                        },
                        {
                            "speaker": "Maria",
                            "text": "I am go to school yesterday",
                            "timestamp": "00:30",
                        },
                    ]
                },
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "## Lesson transcript" in prompt
        assert "[00:15] Teacher: How are you?" in prompt
        assert "[00:30] Maria: I am go to school yesterday" in prompt

    def test_empty_utterances_skips_transcript_section(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "transcript": {"utterances": []},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "## Lesson transcript" not in prompt


class TestSkillOutputInjection:
    def test_error_analysis_included(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "skill_outputs": {
                    SkillName.ANALYZE_ERRORS: {
                        "errors": [
                            {
                                "severity": "moderate",
                                "original": "I go yesterday",
                                "corrected": "I went yesterday",
                                "explanation": "Past simple required",
                            },
                        ],
                    },
                },
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "## Lesson analysis results" in prompt
        assert "### Error analysis" in prompt
        assert "I go yesterday" in prompt
        assert "I went yesterday" in prompt

    def test_themes_included(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "skill_outputs": {
                    SkillName.ANALYZE_THEMES: {
                        "themes": [
                            {
                                "topic": "Travel planning",
                                "vocabulary": ["airport", "boarding pass"],
                            },
                        ],
                    },
                },
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "### Themes covered" in prompt
        assert "Travel planning" in prompt
        assert "airport" in prompt

    def test_level_assessment_included(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "skill_outputs": {
                    SkillName.ANALYZE_LEVEL: {
                        "level": "B1",
                        "framework": "CEFR",
                        "strengths": ["vocabulary range", "fluency"],
                        "gaps": ["past tense accuracy"],
                    },
                },
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "### Level assessment" in prompt
        assert "B1" in prompt
        assert "vocabulary range" in prompt
        assert "past tense accuracy" in prompt

    def test_empty_skill_outputs_skips_section(self):
        context = {
            "lesson": {
                "lesson_date": "2026-03-14",
                "skill_outputs": {},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "## Lesson analysis results" not in prompt


class TestSubjectRegistry:
    def test_language_subject_injects_cefr(self):
        context = {
            "student": {"student_name": "Maria", "level": "B1"},
            "subject": {
                "subject_type": "language",
                "subject_config": {"l1": "Spanish", "l2": "English"},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "CEFR" in prompt
        assert "Spanish -> English" in prompt

    def test_language_student_gets_l1_communication(self):
        context = {
            "subject": {
                "subject_type": "language",
                "subject_config": {"l1": "Spanish", "l2": "English"},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "Write explanations and commentary in Spanish" in prompt

    def test_language_teacher_gets_l1_interference_note(self):
        context = {
            "subject": {
                "subject_type": "language",
                "subject_config": {"l1": "French", "l2": "English"},
            },
        }
        prompt = build_system_prompt("daily_briefing", context=context)
        assert "L1: French" in prompt
        assert "interference" in prompt

    def test_unknown_subject_uses_fallback(self):
        context = {
            "subject": {
                "subject_type": "cooking",
                "subject_config": {"cuisine": "Italian"},
            },
        }
        prompt = build_system_prompt("daily_briefing", context=context)
        assert "cooking" in prompt
        assert "CEFR" not in prompt

    def test_no_subject_defaults_to_language(self):
        prompt = build_system_prompt("daily_briefing")
        assert "CEFR" in prompt

    def test_subject_line_in_student_context(self):
        context = {
            "student": {"student_name": "Maria", "level": "B1"},
            "subject": {
                "subject_type": "language",
                "subject_config": {"l1": "Spanish", "l2": "English"},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "- Subject: Language teaching (Spanish -> English)" in prompt

    def test_no_l1_l2_uses_english_communication(self):
        context = {
            "subject": {
                "subject_type": "language",
                "subject_config": {},
            },
        }
        prompt = build_system_prompt("student_practice", context=context)
        assert "Communicate in English" in prompt
