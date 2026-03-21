from django.db import models

from apps.core.models import TimeStampedModel


class VoiceSession(TimeStampedModel):
    """A voice practice session between a student and the ConvoAI avatar.

    Created when session starts, updated with mastery snapshot on stop.
    Used for teacher briefing: which errors were practiced, quiz results.
    """

    student_id = models.CharField(max_length=255, help_text="Student who practiced")
    lesson_id = models.CharField(max_length=255, help_text="Source lesson for errors/themes")
    agent_id = models.CharField(max_length=255, help_text="Agora ConvoAI agent ID")
    channel = models.CharField(max_length=255, help_text="Agora RTC channel name")
    classtime_session_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Classtime session code for quiz bridge",
    )
    mastery_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Final mastery state: errors, quiz results, biomarkers",
    )
    ended_at = models.DateTimeField(null=True, blank=True, help_text="When session ended")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"VoiceSession {self.id} (student={self.student_id})"
