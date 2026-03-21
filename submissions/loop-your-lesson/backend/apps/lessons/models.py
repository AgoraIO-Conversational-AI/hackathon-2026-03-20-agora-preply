from django.db import models

from apps.core.models import TimeStampedModel


class Lesson(TimeStampedModel):
    teacher = models.ForeignKey("accounts.Teacher", on_delete=models.CASCADE, related_name="lessons")
    subject_type = models.CharField(max_length=50)
    subject_config = models.JSONField(default=dict, blank=True)
    date = models.DateField()
    duration_minutes = models.IntegerField(default=0)
    transcript = models.JSONField(default=dict, blank=True)
    transcript_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Lesson {self.date} - {self.teacher.name}"


class LessonStudent(TimeStampedModel):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="lesson_students")
    student = models.ForeignKey("accounts.Student", on_delete=models.CASCADE, related_name="lesson_students")

    class Meta:
        unique_together = [("lesson", "student")]

    def __str__(self):
        return f"{self.lesson} - {self.student.name}"
