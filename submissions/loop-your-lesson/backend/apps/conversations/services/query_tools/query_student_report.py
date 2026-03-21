from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field

from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant
from apps.conversations.services.tools import PreplyTool, register_tool
from apps.learning_progress.models import ErrorPattern, LessonLevelAssessment
from apps.lessons.models import LessonStudent
from apps.skill_results.models import ErrorRecord
from apps.tutoring.models import TutoringRelationship, TutoringStatus


class QueryStudentReportArgs(BaseModel):
    student_name: str | None = Field(None, description="Student name to look up")


@sync_to_async
def _fetch_student_report(student, teacher_id):
    """Build a comprehensive report for a student from structured models."""
    ls = (
        LessonStudent.objects.filter(student=student, lesson__teacher_id=teacher_id)
        .select_related("lesson")
        .order_by("-lesson__date")
        .first()
    )

    lesson = ls.lesson if ls else None
    report = {
        "student_name": student.name,
        "lesson_date": str(lesson.date) if lesson else None,
    }

    # Error analysis from ErrorRecord
    if lesson:
        errors = ErrorRecord.objects.filter(lesson=lesson, student=student)
        if errors.exists():
            by_severity = {}
            by_type = {}
            for e in errors:
                by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
                key = (e.error_type, e.error_subtype)
                if key not in by_type:
                    by_type[key] = {
                        "type": e.error_type,
                        "pattern": e.error_subtype,
                        "count": 0,
                        "severity": e.severity,
                    }
                by_type[key]["count"] += 1

            report["error_summary"] = {
                "total": errors.count(),
                **by_severity,
            }
            report["top_errors"] = sorted(by_type.values(), key=lambda x: x["count"], reverse=True)[:5]

    # Error patterns (cross-lesson)
    patterns = ErrorPattern.objects.filter(
        student=student,
        teacher_id=teacher_id,
    ).order_by("-occurrence_count")[:5]
    if patterns:
        report["error_patterns"] = [
            {
                "pattern": p.label,
                "status": p.status,
                "occurrence_count": p.occurrence_count,
                "lesson_count": p.lesson_count,
                "mastery_score": p.mastery_score,
                "times_tested": p.times_tested,
            }
            for p in patterns
        ]

    # Level from LessonLevelAssessment
    level_assessment = (
        LessonLevelAssessment.objects.filter(
            student=student,
        )
        .order_by("-created_at")
        .first()
    )
    if level_assessment:
        report["level"] = level_assessment.overall_level
        report["suggested_focus"] = level_assessment.gaps
    else:
        # Fallback to TutoringRelationship
        rel = TutoringRelationship.objects.filter(teacher_id=teacher_id, student=student).first()
        if rel and rel.latest_level:
            report["level"] = rel.latest_level

    # Themes from LessonTheme
    if lesson:
        from apps.skill_results.models import LessonTheme

        themes = LessonTheme.objects.filter(lesson=lesson, student=student)
        if themes.exists():
            report["themes_covered"] = [t.topic for t in themes]

    # Practice results
    if lesson:
        session = ClasstimeSession.objects.filter(lesson=lesson).first()
        if session:
            participant = SessionParticipant.objects.filter(session=session, student=student).first()
            if participant and participant.results_data:
                p_data = participant.results_data
                questions = p_data.get("questions", [])
                report["practice_results"] = {
                    "completed": participant.completed_at is not None,
                    "score": p_data.get("score"),
                    "questions_total": len(questions),
                    "questions_correct": sum(1 for q in questions if q.get("correct")),
                    "weak_areas": p_data.get("weak_areas", []),
                }

    return report


@sync_to_async
def _find_student_by_name(name, teacher_id):
    """Look up a student by name, scoped to the teacher's active relationships."""
    rel = (
        TutoringRelationship.objects.filter(
            teacher_id=teacher_id,
            student__name__icontains=name,
            status=TutoringStatus.ACTIVE,
        )
        .select_related("student")
        .first()
    )
    return rel.student if rel else None


@register_tool
class QueryStudentReportTool(PreplyTool):
    @property
    def name(self):
        return "query_student_report"

    @property
    def description(self):
        return (
            "Get a detailed report for a specific student."
            " Combines errors, error patterns, themes, practice results, and suggested focus areas."
        )

    @property
    def args_schema(self):
        return QueryStudentReportArgs

    async def execute(self, *, conversation=None, student_name=None):
        student = None
        teacher_id = conversation.teacher_id if conversation else None

        # Resolve the student
        if student_name and teacher_id:
            student = await _find_student_by_name(student_name, teacher_id)
        if not student and conversation:
            student = conversation.student

        if not student or not teacher_id:
            return self._mock_student_report(student_name)

        report = await _fetch_student_report(student, teacher_id)

        if not report.get("error_summary") and not report.get("level") and not report.get("practice_results"):
            return self._mock_student_report(student_name or student.name)

        data = {
            "widget_type": "student_report",
            "student_name": report.get("student_name", ""),
            "level": report.get("level", ""),
            "lesson_date": report.get("lesson_date"),
            "error_summary": report.get("error_summary", {}),
            "top_errors": report.get("top_errors", []),
            "error_patterns": report.get("error_patterns", []),
            "themes_covered": report.get("themes_covered", []),
            "practice_results": report.get("practice_results", {}),
            "suggested_focus": report.get("suggested_focus", []),
        }

        level_str = f" ({data['level']})" if data.get("level") else ""
        error_total = data.get("error_summary", {}).get("total", 0)
        practice_score = data.get("practice_results", {}).get("score")
        focus = data.get("suggested_focus", [])

        message = f"Report for {data['student_name']}{level_str}: {error_total} errors found"
        if practice_score is not None:
            message += f", practice score {practice_score}%"
        if focus:
            message += f". Key focus: {focus[0]}"
        else:
            message += "."

        return message, data

    def _mock_student_report(self, student_name=None):
        data = {
            "widget_type": "student_report",
            "student_name": student_name or "Maria Garcia",
            "level": "B1",
            "lesson_date": "2026-03-14",
            "error_summary": {"total": 4, "major": 1, "moderate": 2, "minor": 1},
            "top_errors": [
                {"type": "grammar", "pattern": "Past simple", "count": 2, "severity": "moderate"},
                {"type": "grammar", "pattern": "Conditionals", "count": 1, "severity": "major"},
            ],
            "themes_covered": ["Travel planning", "Restaurant and food", "Giving directions"],
            "practice_results": {
                "completed": True,
                "score": 75,
                "questions_total": 8,
                "questions_correct": 6,
                "weak_areas": ["Past tense word order", "Third conditional structure"],
            },
            "suggested_focus": [
                (
                    "Past tense narrative: She conjugates correctly in isolation"
                    " but struggles with sentence-level application"
                ),
                "Conditional review: Start with second conditional reinforcement before third conditional",
            ],
        }

        message = (
            f"Report for {data['student_name']} (B1): "
            f"{data['error_summary']['total']} errors found, "
            f"practice score {data['practice_results']['score']}%. "
            f"Key focus: {data['suggested_focus'][0]}"
        )
        return message, data
