from django.db import models

from apps.core.models import TimeStampedModel


class SessionType(models.TextChoices):
    PRACTICE = "practice", "Practice"
    ASSESSMENT = "assessment", "Assessment"


class ClasstimeSession(TimeStampedModel):
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="classtime_sessions")
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classtime_sessions",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classtime_sessions",
    )
    question_skill_execution = models.ForeignKey(
        "skill_results.SkillExecution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classtime_sessions",
    )
    session_code = models.CharField(max_length=50, unique=True)
    question_set_id = models.CharField(max_length=100, blank=True)
    session_type = models.CharField(max_length=20, choices=SessionType.choices, default=SessionType.PRACTICE)
    status = models.CharField(max_length=50, default="created")
    questions_data = models.JSONField(default=list, blank=True)
    student_url = models.CharField(max_length=500, blank=True)
    secret_link = models.CharField(max_length=100, blank=True)
    results_data = models.JSONField(default=dict, blank=True)
    results_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "-created_at"]),
            models.Index(fields=["student", "-created_at"]),
            models.Index(fields=["lesson"]),
        ]

    def __str__(self):
        return f"Session {self.session_code} ({self.session_type})"


class SessionParticipant(TimeStampedModel):
    session = models.ForeignKey(ClasstimeSession, on_delete=models.CASCADE, related_name="participants")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="session_participations")
    joined_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    results_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.student.name} in {self.session.session_code}"


class PracticeQuestion(TimeStampedModel):
    """A Classtime question linked to its source error and pattern."""

    session = models.ForeignKey(ClasstimeSession, on_delete=models.CASCADE, related_name="practice_questions")
    error_record = models.ForeignKey(
        "skill_results.ErrorRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="practice_questions",
    )
    error_pattern = models.ForeignKey(
        "learning_progress.ErrorPattern",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="practice_questions",
    )
    question_index = models.IntegerField()
    classtime_question_id = models.CharField(max_length=100, blank=True)
    question_type = models.CharField(max_length=50)
    difficulty = models.CharField(max_length=50, blank=True)
    stem = models.TextField()
    source_error_ref = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "question_index"]),
            models.Index(fields=["error_record"]),
            models.Index(fields=["error_pattern"]),
        ]

    def __str__(self):
        return f"Q{self.question_index} ({self.question_type}) - {self.session}"


class PracticeResult(TimeStampedModel):
    """A student's answer to a specific practice question."""

    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name="practice_results")
    practice_question = models.ForeignKey(PracticeQuestion, on_delete=models.CASCADE, related_name="results")
    is_correct = models.BooleanField()
    student_answer = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["participant", "-answered_at"]),
            models.Index(fields=["practice_question", "is_correct"]),
        ]

    def __str__(self):
        status = "correct" if self.is_correct else "incorrect"
        return f"{status} - {self.practice_question}"
