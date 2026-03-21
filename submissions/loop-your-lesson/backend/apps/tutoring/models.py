from django.db import models

from apps.core.models import TimeStampedModel


class TutoringStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"


class TutoringRelationship(TimeStampedModel):
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="tutoring_relationships")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="tutoring_relationships")
    subject_type = models.CharField(max_length=50)
    subject_config = models.JSONField(default=dict, blank=True)
    current_level = models.CharField(max_length=50, blank=True)
    goal = models.TextField(blank=True)
    schedule = models.CharField(max_length=255, blank=True)
    total_lessons = models.IntegerField(default=0)
    last_lesson_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=TutoringStatus.choices, default=TutoringStatus.ACTIVE, db_index=True
    )
    preply_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    latest_level = models.CharField(max_length=10, blank=True)
    latest_level_assessed_at = models.DateTimeField(null=True, blank=True)
    active_error_patterns = models.IntegerField(default=0)
    mastered_error_patterns = models.IntegerField(default=0)

    class Meta:
        unique_together = [("teacher", "student", "subject_type")]

    def __str__(self):
        return f"{self.teacher.name} -> {self.student.name} ({self.subject_type})"
