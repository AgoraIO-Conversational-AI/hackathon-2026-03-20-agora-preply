from django.db import models

from apps.core.models import TimeStampedModel


class DailyBriefing(TimeStampedModel):
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="daily_briefings")
    date = models.DateField(db_index=True)
    briefing_data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("teacher", "date")]

    def __str__(self):
        return f"Briefing {self.date} - {self.teacher.name}"
