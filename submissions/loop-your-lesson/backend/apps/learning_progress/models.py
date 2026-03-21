from django.db import models

from apps.core.models import TimeStampedModel


class ErrorPatternStatus(models.TextChoices):
    NEW = "new", "New"
    RECURRING = "recurring", "Recurring"
    IMPROVING = "improving", "Improving"
    MASTERED = "mastered", "Mastered"


class ErrorPattern(TimeStampedModel):
    """A recurring error pattern tracked across lessons for a student."""

    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="error_patterns")
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="student_error_patterns")
    pattern_key = models.CharField(max_length=200)
    label = models.CharField(max_length=255)
    error_type = models.CharField(max_length=50)
    error_subtype = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ErrorPatternStatus.choices,
        default=ErrorPatternStatus.NEW,
        db_index=True,
    )
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    occurrence_count = models.IntegerField(default=1)
    lesson_count = models.IntegerField(default=1)
    times_tested = models.IntegerField(default=0)
    times_correct = models.IntegerField(default=0)
    mastery_score = models.FloatField(null=True, blank=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("student", "teacher", "pattern_key")]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["student", "-occurrence_count"]),
            models.Index(fields=["teacher", "student", "status"]),
        ]

    def __str__(self):
        return f"{self.label} ({self.status}) - {self.student}"


class ErrorPatternOccurrence(TimeStampedModel):
    """Links an error pattern to a specific error record in a lesson."""

    pattern = models.ForeignKey(ErrorPattern, on_delete=models.CASCADE, related_name="occurrences")
    error_record = models.ForeignKey(
        "skill_results.ErrorRecord", on_delete=models.CASCADE, related_name="pattern_occurrences"
    )
    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.CASCADE, related_name="error_pattern_occurrences")

    class Meta:
        unique_together = [("pattern", "error_record")]
        indexes = [
            models.Index(fields=["pattern", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.pattern.label} in {self.lesson}"


class LessonLevelAssessment(TimeStampedModel):
    """CEFR level assessment from a single lesson."""

    skill_execution = models.ForeignKey(
        "skill_results.SkillExecution",
        on_delete=models.CASCADE,
        related_name="level_assessments",
    )
    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.CASCADE, related_name="level_assessments")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="level_assessments")
    overall_level = models.CharField(max_length=10)
    range_level = models.CharField(max_length=10, blank=True)
    accuracy_level = models.CharField(max_length=10, blank=True)
    fluency_level = models.CharField(max_length=10, blank=True)
    interaction_level = models.CharField(max_length=10, blank=True)
    coherence_level = models.CharField(max_length=10, blank=True)
    strengths = models.JSONField(default=list)
    gaps = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)
    zpd_lower = models.CharField(max_length=10, blank=True)
    zpd_upper = models.CharField(max_length=10, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "-created_at"]),
            models.Index(fields=["student", "overall_level"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.overall_level} ({self.lesson})"
