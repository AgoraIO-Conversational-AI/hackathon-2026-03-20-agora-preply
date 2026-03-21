# ruff: noqa: E501
"""Seed demo data from emulated lesson fixtures."""

import copy
import json
import logging
import random
from datetime import UTC, date, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.accounts.models import Student, Teacher
from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant
from apps.classtime_sessions.services.auth import ensure_teacher_token
from apps.classtime_sessions.services.sessions import create_practice_for_lesson
from apps.conversations.models import Conversation, ConversationManager
from apps.lessons.models import Lesson, LessonStudent
from apps.skill_results.services import complete_execution, create_execution, start_execution
from apps.tutoring.models import TutoringRelationship

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "emulated_lessons"

TEACHERS = [
    {"name": "Sarah", "email": "teacher-sarah@demo.preply.com", "preply_user_id": "teacher-sarah"},
    {"name": "James", "email": "teacher-james@demo.preply.com", "preply_user_id": "teacher-james"},
    {"name": "Miguel", "email": "teacher-miguel@demo.preply.com", "preply_user_id": "teacher-miguel"},
    {"name": "Rachel", "email": "teacher-rachel@demo.preply.com", "preply_user_id": "teacher-rachel"},
]

STUDENTS = [
    {"name": "Lukas", "email": "student-lukas@demo.preply.com", "preply_user_id": "student-lukas"},
    {"name": "Katrin", "email": "student-katrin@demo.preply.com", "preply_user_id": "student-katrin"},
    {"name": "Carmen", "email": "student-carmen@demo.preply.com", "preply_user_id": "student-carmen"},
    {"name": "Pablo", "email": "student-pablo@demo.preply.com", "preply_user_id": "student-pablo"},
    {"name": "Oksana", "email": "student-oksana@demo.preply.com", "preply_user_id": "student-oksana"},
    {"name": "Andrii", "email": "student-andrii@demo.preply.com", "preply_user_id": "student-andrii"},
]

# Lesson -> teacher/student mapping (keyed by lesson_id from emulated-index.json)
LESSON_MAPPING = {
    "emu-de-en-a1-01": {"teacher": "James", "student": "Lukas"},
    "emu-de-en-b2-01": {"teacher": "James", "student": "Katrin"},
    "emu-es-en-a1-01": {"teacher": "Miguel", "student": "Carmen"},
    "emu-es-en-b2-01": {"teacher": "Rachel", "student": "Pablo"},
    "emu-uk-en-a1-01": {"teacher": "Sarah", "student": "Oksana"},
    "emu-uk-en-a1-02": {"teacher": "Sarah", "student": "Oksana"},
    "emu-uk-en-b2-01": {"teacher": "Rachel", "student": "Andrii"},
}

DATE_OVERRIDES = {
    "emu-de-en-a1-01": date(2026, 3, 17),
    "emu-de-en-b2-01": date(2026, 3, 18),
    "emu-es-en-a1-01": date(2026, 3, 17),
    "emu-es-en-b2-01": date(2026, 3, 19),
    "emu-uk-en-a1-01": date(2026, 3, 17),
    "emu-uk-en-a1-02": date(2026, 3, 19),
    "emu-uk-en-b2-01": date(2026, 3, 18),
}

ANALYSIS_SKILLS = [
    ("analyze-lesson-errors", "analyze-lesson-errors.json"),
    ("analyze-lesson-level", "analyze-lesson-level.json"),
    ("analyze-lesson-themes", "analyze-lesson-themes.json"),
]

GOAL_BY_LEVEL = {
    "A1": "Build basic English communication",
    "A2": "Develop everyday conversational confidence",
    "B1": "Strengthen fluency for work and social contexts",
    "B2": "Advanced fluency and academic English",
}

SCHEDULE_BY_LEVEL = {
    "A1": "Mon/Wed 10:00",
    "A2": "Tue/Thu 11:30",
    "B1": "Mon/Wed/Fri 14:00",
    "B2": "Tue/Thu 15:00",
}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed demo data from emulated lesson fixtures"

    def handle(self, *args, **options):
        self._flush_old_data()
        index = self._load_index()
        teachers = self._create_teachers()
        students = self._create_students()
        self._create_relationships(teachers, students, index)
        lessons = self._create_lessons(teachers, students, index)
        self._create_skill_executions(teachers, students, lessons, index)
        self._create_classtime_sessions(teachers, students, lessons, index)
        self._create_question_executions(teachers, students, lessons, index)
        self._create_demo_conversations(teachers, students, lessons)
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))

    # ------------------------------------------------------------------
    # Fixture loading
    # ------------------------------------------------------------------

    def _load_index(self):
        with open(FIXTURES_DIR / "emulated-index.json") as f:
            return json.load(f)["transcripts"]

    def _load_fixture(self, lesson_id, filename):
        with open(FIXTURES_DIR / lesson_id / filename) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def _flush_old_data(self):
        """Remove previous demo data so the command is idempotent."""
        # New demo data
        Teacher.objects.filter(email__endswith="@demo.preply.com").delete()
        Student.objects.filter(email__endswith="@demo.preply.com").delete()
        # Old seed data (pre-emulated)
        Teacher.objects.filter(email="teacher@preply.com").delete()
        Student.objects.filter(email__in=[
            "maria@example.com", "alex@example.com",
            "sophie@example.com", "klaus@example.com",
        ]).delete()
        Conversation.objects.filter(title__in=["Today's lesson prep", "My lesson review"]).delete()
        self.stdout.write("Flushed old demo data.")

    # ------------------------------------------------------------------
    # Core entities
    # ------------------------------------------------------------------

    def _create_teachers(self):
        """Create teacher records and provision Classtime accounts.

        If CLASSTIME_ADMIN_TOKEN is set, each teacher gets a Classtime account
        and a cached 7-day JWT. This is needed for session creation and Pusher auth.
        """
        use_classtime = bool(getattr(settings, "CLASSTIME_ADMIN_TOKEN", ""))
        teachers = {}
        for td in TEACHERS:
            teacher, _ = Teacher.objects.get_or_create(
                preply_user_id=td["preply_user_id"],
                defaults=td,
            )
            if use_classtime:
                try:
                    ensure_teacher_token(teacher)
                    self.stdout.write(f"  Teacher: {teacher.name} (ct_id={teacher.classtime_account_id}, token cached)")
                except Exception as e:
                    logger.warning("Could not provision Classtime for %s: %s", teacher.name, e)
                    self.stdout.write(self.style.WARNING(f"  Teacher: {teacher.name} (Classtime failed: {e})"))
            else:
                self.stdout.write(f"  Teacher: {teacher.name}")
            teachers[teacher.name] = teacher
        return teachers

    def _create_students(self):
        """Create student records, return dict keyed by name."""
        students = {}
        for sd in STUDENTS:
            student, _ = Student.objects.get_or_create(
                preply_user_id=sd["preply_user_id"],
                defaults=sd,
            )
            students[student.name] = student
            self.stdout.write(f"  Student: {student.name}")
        return students

    def _create_relationships(self, teachers, students, index):
        """Create one TutoringRelationship per unique teacher-student pair."""
        # Count lessons per teacher-student pair
        pair_lessons = {}
        for entry in index:
            mapping = LESSON_MAPPING[entry["lesson_id"]]
            key = (mapping["teacher"], mapping["student"])
            pair_lessons.setdefault(key, []).append(entry)

        count = 0
        for (teacher_name, student_name), entries in pair_lessons.items():
            teacher = teachers[teacher_name]
            student = students[student_name]
            first_entry = entries[0]

            transcript = self._load_fixture(first_entry["lesson_id"], "transcript.json")
            subject_config = transcript.get("subject_config", {})
            level = first_entry["level"]

            TutoringRelationship.objects.get_or_create(
                teacher=teacher,
                student=student,
                subject_type="language",
                defaults={
                    "subject_config": subject_config,
                    "current_level": level,
                    "goal": GOAL_BY_LEVEL.get(level, "Improve English proficiency"),
                    "total_lessons": len(entries),
                    "schedule": SCHEDULE_BY_LEVEL.get(level, "Mon/Wed 10:00"),
                    "status": "active",
                },
            )
            count += 1
        self.stdout.write(f"  Created {count} tutoring relationships.")

    # ------------------------------------------------------------------
    # Lessons
    # ------------------------------------------------------------------

    def _create_lessons(self, teachers, students, index):
        """Create Lesson + LessonStudent for each entry in the index.

        Returns dict keyed by lesson_id -> (lesson, teacher, student).
        """
        lessons = {}
        for entry in index:
            lesson_id = entry["lesson_id"]
            mapping = LESSON_MAPPING[lesson_id]
            teacher = teachers[mapping["teacher"]]
            student = students[mapping["student"]]

            transcript = self._load_fixture(lesson_id, "transcript.json")
            lesson_date = DATE_OVERRIDES.get(lesson_id, date.fromisoformat(transcript.get("date", "2026-03-20")))

            lesson, _ = Lesson.objects.get_or_create(
                teacher=teacher,
                date=lesson_date,
                transcript_summary=f"{entry['theme']} lesson with {student.name}",
                defaults={
                    "subject_type": "language",
                    "subject_config": transcript.get("subject_config", {}),
                    "duration_minutes": entry.get("duration_minutes", 55),
                    "transcript": transcript,
                },
            )
            LessonStudent.objects.get_or_create(lesson=lesson, student=student)
            lessons[lesson_id] = (lesson, teacher, student)
            self.stdout.write(f"  Lesson: {lesson.date} ({lesson_id})")
        return lessons

    # ------------------------------------------------------------------
    # Skill executions (4 per lesson, using complete_execution for parsing)
    # ------------------------------------------------------------------

    def _create_skill_executions(self, teachers, students, lessons, index):
        """Create SkillExecutions using the service layer so parsers run.

        Analysis skills (errors, level, themes) run first. Question skill runs
        after ClasstimeSessions exist so PracticeQuestion rows can be linked.
        """
        count = 0
        for lesson_id, (lesson, teacher, student) in lessons.items():
            for skill_name, filename in ANALYSIS_SKILLS:
                output_data = self._load_fixture(lesson_id, filename)
                execution = create_execution(teacher, skill_name, lesson=lesson, student=student)
                start_execution(execution)
                complete_execution(execution, output_data)
                count += 1
        self.stdout.write(f"  Created {count} analysis skill executions.")

    def _create_question_executions(self, teachers, students, lessons, index):
        """Create question SkillExecutions after sessions exist for PracticeQuestion linking."""
        count = 0
        for lesson_id, (lesson, teacher, student) in lessons.items():
            output_data = self._load_fixture(lesson_id, "questions.json")
            execution = create_execution(teacher, "generate-classtime-questions", lesson=lesson, student=student)
            start_execution(execution)
            complete_execution(execution, output_data)
            count += 1
        self.stdout.write(f"  Created {count} question skill executions.")

    # ------------------------------------------------------------------
    # Classtime sessions with synthetic results
    # ------------------------------------------------------------------

    def _create_classtime_sessions(self, teachers, students, lessons, index):
        """Create ClasstimeSession + SessionParticipant.

        If CLASSTIME_ADMIN_TOKEN is set, creates real Classtime sessions via the
        API (solo session + setSessionSettings). Students get clickable /code/ URLs.

        Falls back to synthetic sessions (fake codes, no URLs) if Classtime is
        unavailable or the API call fails.
        """
        use_classtime = bool(getattr(settings, "CLASSTIME_ADMIN_TOKEN", ""))
        if use_classtime:
            self.stdout.write("  Classtime API available - creating live sessions...")
        else:
            self.stdout.write("  No CLASSTIME_ADMIN_TOKEN - creating synthetic sessions.")

        live_count = 0
        synthetic_count = 0
        for lesson_id, (lesson, teacher, student) in lessons.items():
            questions_data = self._load_fixture(lesson_id, "questions.json")
            results_data = self._generate_results(questions_data, lesson_id)

            # Try real Classtime session
            if use_classtime:
                try:
                    skill_output = copy.deepcopy(questions_data)
                    self._fix_empty_gap_solutions(skill_output)
                    session = create_practice_for_lesson(
                        teacher=teacher,
                        student=student,
                        skill_output=skill_output,
                        lesson=lesson,
                    )
                    # Backfill synthetic results onto the live session
                    session.results_data = results_data
                    session.save(update_fields=["results_data"])
                    self.stdout.write(f"    LIVE {lesson_id}: {session.student_url}")
                    live_count += 1
                    continue
                except Exception as e:
                    logger.warning("Classtime failed for %s, falling back to synthetic: %s", lesson_id, e)
                    self.stdout.write(self.style.WARNING(f"    FALLBACK {lesson_id}: {e}"))

            # Synthetic fallback
            session_code = f"PLI-{lesson_id}"
            session, _ = ClasstimeSession.objects.get_or_create(
                session_code=session_code,
                defaults={
                    "lesson": lesson,
                    "teacher": teacher,
                    "student": student,
                    "session_type": "practice",
                    "status": "completed",
                    "questions_data": questions_data.get("questions", []),
                    "results_data": results_data,
                },
            )

            joined = datetime(2026, lesson.date.month, lesson.date.day, 10, 0, tzinfo=UTC)
            completed = datetime(2026, lesson.date.month, lesson.date.day, 10, 15, tzinfo=UTC)

            SessionParticipant.objects.get_or_create(
                session=session,
                student=student,
                defaults={
                    "joined_at": joined,
                    "completed_at": completed,
                    "results_data": results_data,
                },
            )
            synthetic_count += 1

        self.stdout.write(f"  Created {live_count} live + {synthetic_count} synthetic Classtime sessions.")

    @staticmethod
    def _fix_empty_gap_solutions(skill_output):
        """Convert blank gaps with empty solutions to choices dropdowns.

        Classtime's soloSession endpoint crashes on questions with empty-string
        gap solutions (e.g. zero-article exercises where the answer is "nothing").
        Convert these to choices with a "—" (no article) option instead.
        """
        for q in skill_output.get("questions", []):
            if q.get("payload_type") != "gap":
                continue
            for gap in q.get("payload", {}).get("gaps", []):
                if gap.get("type") == "blank" and not gap.get("solution"):
                    gap["type"] = "choices"
                    gap.pop("solution", None)
                    gap["choices"] = [
                        {"content": "the", "is_correct": False},
                        {"content": "a", "is_correct": False},
                        {"content": "\u2014", "is_correct": True},
                    ]

    def _generate_results(self, questions_data, lesson_id):
        """Generate deterministic practice results."""
        rng = random.Random(lesson_id)
        questions = questions_data.get("questions", [])
        results = []
        for i, q in enumerate(questions):
            difficulty = q.get("difficulty", "zpd_target")
            correct_prob = {"zpd_lower": 0.85, "zpd_target": 0.6, "zpd_stretch": 0.4}.get(difficulty, 0.6)
            is_correct = rng.random() < correct_prob
            results.append({
                "question_id": f"q-{i}",
                "correct": is_correct,
                "student_answer": "",
                "question_title": q.get("payload", {}).get("title", ""),
                "question_type": q.get("payload_type", ""),
                "source_error": q.get("source_ref"),
            })

        correct_count = sum(1 for r in results if r["correct"])
        return {
            "score": correct_count,
            "total": len(results),
            "percentage": round(correct_count / len(results) * 100) if results else 0,
            "questions": results,
        }

    # ------------------------------------------------------------------
    # Demo conversations (2 pre-seeded multi-turn chats)
    # ------------------------------------------------------------------

    def _create_demo_conversations(self, teachers, students, lessons):
        sarah = teachers["Sarah"]
        oksana = students["Oksana"]
        lukas = students["Lukas"]
        james = teachers["James"]

        oksana_lesson = lessons["emu-uk-en-a1-01"][0]
        lukas_lesson = lessons["emu-de-en-a1-01"][0]

        self._create_daily_briefing_conversation(sarah, oksana, oksana_lesson)
        self._create_student_practice_conversation(james, lukas, lukas_lesson)
        self.stdout.write("  Created 2 demo conversations.")

    def _create_daily_briefing_conversation(self, teacher, oksana, lesson):
        """Conversation 1: daily_briefing for Teacher Sarah - 3 turns."""
        cm = ConversationManager
        conv = cm.create_conversation(mode="daily_briefing", teacher=teacher, lesson=lesson)
        conv.title = "Today's lesson prep"
        conv.status = "completed"
        conv.save()

        # --- Turn 1: "Show today's overview" ---
        cm.add_user_message(conv, "Show today's overview")

        overview_data = {
            "widget_type": "daily_overview",
            "date": "2026-03-21",
            "students": [
                {
                    "name": "Oksana",
                    "level": "A1",
                    "lessons_completed": 2,
                    "practice_completed": True,
                    "practice_score": 57,
                    "error_count": 15,
                    "attention_flag": "Article omission persists across 2 lessons. Third person -s improving.",
                    "schedule": "Mon/Wed 10:00",
                },
            ],
        }
        overview_message = "1 student today. Oksana has 2 lessons analyzed with cross-lesson patterns."

        tc1_id = "tc_overview_1"
        tool_calls_1 = [{"id": tc1_id, "name": "query_daily_overview", "input": {}}]
        process_steps_1 = [
            {
                "type": "thinking",
                "content": "The teacher wants to see today's overview. I'll pull up all students with their practice status and error counts.",
            },
            {
                "type": "tool_call",
                "toolName": "query_daily_overview",
                "toolId": tc1_id,
                "toolInput": {},
                "status": "completed",
                "result": {"message": overview_message, "data": overview_data, "executionTimeMs": 23},
            },
        ]

        asst1_tool = cm.add_assistant_message(
            conv,
            "",
            tool_calls=tool_calls_1,
            stop_reason="tool_use",
            metadata={"process_steps": process_steps_1},
        )
        cm.record_tool_execution(
            conv, asst1_tool, "query_daily_overview", tc1_id, {},
            success=True, result_message=overview_message, result_data=overview_data, execution_time_ms=23,
        )
        cm.add_tool_result(conv, tc1_id, "query_daily_overview", overview_message)

        cm.add_assistant_message(
            conv,
            "Here's your overview for today:\n\n"
            "**Oksana** (A1, Mon/Wed 10:00) - 2 lessons analyzed\n"
            "- Practice score: 57% (last session)\n"
            "- 15 errors across 2 lessons\n"
            "- **Recurring pattern:** Article omission persists in both lessons - typical Ukrainian L1 transfer\n"
            "- **Improving:** Third person -s was frequent in lesson 1 but less so in lesson 2\n\n"
            "The cross-lesson data shows article omission is her most persistent pattern. It appeared in both the shopping lesson and the daily routine lesson. This is a priority for today.",
            stop_reason="end_turn",
        )

        # --- Turn 2: "Tell me more about Oksana" ---
        cm.add_user_message(conv, "Tell me more about Oksana")

        report_data = {
            "widget_type": "student_report",
            "student_name": "Oksana",
            "level": "A1",
            "lessons_analyzed": 2,
            "lesson_dates": ["2026-03-17", "2026-03-19"],
            "error_summary": {"total": 15, "recurring_patterns": 3, "improving": 1, "new": 2},
            "themes_covered": ["Shopping and food", "Daily routine and time"],
            "practice_results": {"completed": True, "score": 57, "questions_total": 7, "questions_correct": 4},
            "cross_lesson_patterns": [
                {"pattern": "Article omission", "status": "recurring", "lessons": 2},
                {"pattern": "Third person -s", "status": "improving", "lessons": 2},
                {"pattern": "Plural -s errors", "status": "recurring", "lessons": 2},
            ],
            "suggested_focus": [
                "Drill article usage with concrete nouns - persists across both lessons",
                "Third person -s is improving - reinforce with positive practice",
            ],
        }
        report_message = "Report for Oksana (A1): 2 lessons, 15 errors, 3 recurring patterns. Practice score 57%."

        tc2_id = "tc_report_1"
        tool_calls_2 = [{"id": tc2_id, "name": "query_student_report", "input": {"student_name": "Oksana"}}]
        process_steps_2 = [
            {
                "type": "thinking",
                "content": "The teacher is asking about Oksana specifically. I'll pull her full report.",
            },
            {
                "type": "tool_call",
                "toolName": "query_student_report",
                "toolId": tc2_id,
                "toolInput": {"student_name": "Oksana"},
                "status": "completed",
                "result": {"message": report_message, "data": report_data, "executionTimeMs": 18},
            },
        ]

        asst2_tool = cm.add_assistant_message(
            conv,
            "",
            tool_calls=tool_calls_2,
            stop_reason="tool_use",
            metadata={"process_steps": process_steps_2},
        )
        cm.record_tool_execution(
            conv, asst2_tool, "query_student_report", tc2_id, {"student_name": "Oksana"},
            success=True, result_message=report_message, result_data=report_data, execution_time_ms=18,
        )
        cm.add_tool_result(conv, tc2_id, "query_student_report", report_message)

        cm.add_assistant_message(
            conv,
            "Here's Oksana's progress across 2 lessons (Mar 17 shopping, Mar 19 daily routine):\n\n"
            "**Level:** A1 | **2 lessons analyzed**\n\n"
            "**Cross-lesson patterns:**\n"
            "1. **Article omission** (recurring, 2 lessons) - consistently drops articles before nouns in both lessons. This is her #1 priority - Ukrainian has no articles so this is pure acquisition territory.\n"
            "2. **Plural -s errors** (recurring, 2 lessons) - forgets plural marking on countable nouns in both shopping and routine contexts.\n"
            "3. **Third person -s** (improving) - was frequent in lesson 1 but appeared less in lesson 2. The practice drills may be helping.\n\n"
            "**Practice:** 4/7 correct (57%) on last session.\n\n"
            "The good news: third person -s is trending in the right direction. The article pattern needs more intensive work - it's persisting because it requires building a grammatical category that doesn't exist in her L1.",
            stop_reason="end_turn",
        )

        # --- Turn 3: "What should I focus on?" (no tool call) ---
        cm.add_user_message(conv, "What should I focus on with her today?")
        cm.add_assistant_message(
            conv,
            "Based on her error patterns and practice results, I'd prioritize two areas:\n\n"
            "**1. Articles with concrete nouns** - Ukrainian has no article system at all, so this is pure acquisition territory. Start simple:\n"
            "- Use objects in the room: 'This is **a** pen. Give me **the** pen.'\n"
            "- Shopping role-play: 'I want **a** banana. Where is **the** milk?'\n\n"
            "**2. Plural -s with food vocabulary** - She already knows the food words from last lesson, so adding the plural marker is a natural next step:\n"
            "- 'One banana, two banana**s**. One apple, three apple**s**.'\n\n"
            "Keep the L1 insertions low-pressure - at A1, some code-switching is normal and shows she's trying to communicate. The articles and plurals are the structural priorities.",
            stop_reason="end_turn",
        )

    def _create_student_practice_conversation(self, teacher, student, lesson):
        """Conversation 2: student_practice for Lukas - 3 turns."""
        cm = ConversationManager
        conv = cm.create_conversation(mode="student_practice", teacher=teacher, student=student, lesson=lesson)
        conv.title = "My lesson review"
        conv.status = "completed"
        conv.save()

        # --- Turn 1: "What errors should I focus on?" ---
        cm.add_user_message(conv, "What errors should I focus on?")

        errors_data = {
            "widget_type": "error_analysis",
            "errors": [
                {
                    "type": "grammar",
                    "severity": "major",
                    "original": "I go with the car.",
                    "corrected": "I go by car.",
                    "explanation": "In English, we use 'by' for means of transport: by car, by bus, by train.",
                    "reasoning": "German L1 transfer: 'mit dem Auto' -> 'with the car'",
                },
                {
                    "type": "grammar",
                    "severity": "major",
                    "original": "She take the underground.",
                    "corrected": "She takes the underground.",
                    "explanation": "Third person singular (he/she/it) needs -s in present simple.",
                    "reasoning": "Third person -s omission, common at A1",
                },
                {
                    "type": "vocabulary",
                    "severity": "moderate",
                    "original": "I become angry.",
                    "corrected": "I get angry.",
                    "explanation": "'Become' and 'get' are different. 'Get angry' is natural English. 'Become' is a false friend from German 'bekommen'.",
                    "reasoning": "German false friend: bekommen means 'to receive', not 'to become'",
                },
            ],
            "summary": {"total": 3, "by_type": {"grammar": 2, "vocabulary": 1}},
        }
        errors_message = "Found 14 errors. 3 major, 5 moderate, 6 minor."

        tc1_id = "tc_student_errors_1"
        tool_calls_1 = [{"id": tc1_id, "name": "query_lesson_errors", "input": {}}]
        process_steps_1 = [
            {
                "type": "thinking",
                "content": "The student wants to know which errors to prioritize. I'll get the error analysis.",
            },
            {
                "type": "tool_call",
                "toolName": "query_lesson_errors",
                "toolId": tc1_id,
                "toolInput": {},
                "status": "completed",
                "result": {"message": errors_message, "data": errors_data, "executionTimeMs": 14},
            },
        ]

        asst1_tool = cm.add_assistant_message(
            conv,
            "",
            tool_calls=tool_calls_1,
            stop_reason="tool_use",
            metadata={"process_steps": process_steps_1},
        )
        cm.record_tool_execution(
            conv, asst1_tool, "query_lesson_errors", tc1_id, {},
            success=True, result_message=errors_message, result_data=errors_data, execution_time_ms=14,
        )
        cm.add_tool_result(conv, tc1_id, "query_lesson_errors", errors_message)

        cm.add_assistant_message(
            conv,
            "From your lesson on getting around the city, here are the most important errors to focus on:\n\n"
            "**1. Transport prepositions** - You said 'I go **with** the car' but it should be 'I go **by** car'. In English, we always use 'by' for transport: by car, by bus, by train. In German you use 'mit', but English uses 'by'.\n\n"
            "**2. Third person -s** - You said 'She **take** the underground' but it should be 'She **takes**'. When the subject is he/she/it, the verb needs an -s ending.\n\n"
            "**3. False friend: become vs get** - You said 'I **become** angry' but it should be 'I **get** angry'. This is a tricky one from German - 'bekommen' looks like 'become' but they mean different things!\n\n"
            "Want me to explain any of these in more detail?",
            stop_reason="end_turn",
        )

        # --- Turn 2: "How did I do on practice?" ---
        cm.add_user_message(conv, "How did I do on practice?")

        practice_data = {
            "widget_type": "practice_results",
            "session_code": "PLI-emu-de-en-a1-01",
            "completed": True,
            "score": 5,
            "total": 7,
            "percentage": 71,
        }
        practice_message = "Practice results: 5/7 correct (71%)."

        tc2_id = "tc_student_practice_1"
        tool_calls_2 = [{"id": tc2_id, "name": "query_classtime_results", "input": {}}]
        process_steps_2 = [
            {
                "type": "thinking",
                "content": "Student wants to see their practice results. I'll pull the Classtime session data.",
            },
            {
                "type": "tool_call",
                "toolName": "query_classtime_results",
                "toolId": tc2_id,
                "toolInput": {},
                "status": "completed",
                "result": {"message": practice_message, "data": practice_data, "executionTimeMs": 11},
            },
        ]

        asst2_tool = cm.add_assistant_message(
            conv,
            "",
            tool_calls=tool_calls_2,
            stop_reason="tool_use",
            metadata={"process_steps": process_steps_2},
        )
        cm.record_tool_execution(
            conv, asst2_tool, "query_classtime_results", tc2_id, {},
            success=True, result_message=practice_message, result_data=practice_data, execution_time_ms=11,
        )
        cm.add_tool_result(conv, tc2_id, "query_classtime_results", practice_message)

        cm.add_assistant_message(
            conv,
            "You scored **5/7 (71%)** on your transport and directions practice. That's a solid start!\n\n"
            "You got the easier recognition questions right - like choosing 'by' instead of 'with' for transport, and picking the correct verb form. The questions you missed were the harder production ones where you had to write the answer yourself.\n\n"
            "That's actually a normal pattern at A1 - recognizing the right answer is easier than producing it from memory. Keep practicing and the production will come.",
            stop_reason="end_turn",
        )

        # --- Turn 3: "Why is 'I go with the car' wrong?" (no tool call) ---
        cm.add_user_message(conv, "Why is 'I go with the car' wrong?")
        cm.add_assistant_message(
            conv,
            "Great question! In German, you say 'Ich fahre **mit** dem Auto' - with the car. So it feels natural to translate it directly.\n\n"
            "But English uses different prepositions for transport:\n"
            "- **by** + transport (no article): by car, by bus, by train, by plane\n"
            "- **on** + specific vehicle: on the bus, on the train\n"
            "- **in** + car specifically: in the car, in a taxi\n\n"
            "So you can say:\n"
            "- 'I go **by car**' (general)\n"
            "- 'I'm **in the car**' (you're inside it right now)\n\n"
            "But never 'with the car' - in English, 'with' means you have something accompanying you, like 'I go with my friend'.\n\n"
            "A good trick: for how you travel, always start with **by**.",
            stop_reason="end_turn",
        )
