from enum import StrEnum

from django.db import models

from apps.core.models import TimeStampedModel


class SkillName(StrEnum):
    ANALYZE_ERRORS = "analyze-lesson-errors"
    ANALYZE_THEMES = "analyze-lesson-themes"
    ANALYZE_LEVEL = "analyze-lesson-level"
    GENERATE_QUESTIONS = "generate-classtime-questions"


class SkillExecutionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class SkillExecution(TimeStampedModel):
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="skill_executions")
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="skill_executions",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="skill_executions",
    )
    skill_name = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=SkillExecutionStatus.choices,
        default=SkillExecutionStatus.PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    output_log = models.TextField(blank=True)
    error = models.TextField(blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(lesson__isnull=False) | models.Q(student__isnull=False),
                name="skill_exec_requires_lesson_or_student",
            ),
        ]

    def __str__(self):
        return f"{self.skill_name} ({self.status})"


class ErrorRecord(TimeStampedModel):
    """A single error extracted from a lesson's error analysis."""

    skill_execution = models.ForeignKey(SkillExecution, on_delete=models.CASCADE, related_name="error_records")
    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.CASCADE, related_name="error_records")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="error_records")
    error_type = models.CharField(max_length=50, db_index=True)
    error_subtype = models.CharField(max_length=100, blank=True)
    severity = models.CharField(max_length=20, db_index=True)
    communicative_impact = models.CharField(max_length=20, blank=True)
    original_text = models.TextField()
    corrected_text = models.TextField()
    explanation = models.TextField()
    reasoning = models.TextField(blank=True)
    l1_transfer = models.BooleanField(default=False)
    l1_transfer_explanation = models.TextField(blank=True)
    correction_strategy = models.CharField(max_length=50, blank=True)
    utterance_index = models.IntegerField(null=True, blank=True)
    timestamp = models.CharField(max_length=20, blank=True)
    source_error_index = models.IntegerField()
    exercise_priority = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "error_type", "-created_at"]),
            models.Index(fields=["student", "error_subtype"]),
            models.Index(fields=["lesson"]),
        ]

    def __str__(self):
        return f"#{self.source_error_index} {self.error_type}/{self.error_subtype} ({self.severity})"


class LessonTheme(TimeStampedModel):
    """A theme/topic extracted from a lesson."""

    skill_execution = models.ForeignKey(SkillExecution, on_delete=models.CASCADE, related_name="lesson_themes")
    lesson = models.ForeignKey("lessons.Lesson", on_delete=models.CASCADE, related_name="lesson_themes")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="lesson_themes")
    topic = models.CharField(max_length=255)
    communicative_function = models.CharField(max_length=100, blank=True)
    initiated_by = models.CharField(max_length=50, blank=True)
    vocabulary_active = models.JSONField(default=list)
    vocabulary_passive = models.JSONField(default=list)
    chunks = models.JSONField(default=list)
    transcript_range_start = models.CharField(max_length=20, blank=True)
    transcript_range_end = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "-created_at"]),
            models.Index(fields=["lesson"]),
        ]

    def __str__(self):
        return f"{self.topic} ({self.lesson})"
