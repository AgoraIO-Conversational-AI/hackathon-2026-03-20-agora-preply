from django.contrib import admin

from apps.lessons.models import Lesson, LessonStudent


class LessonStudentInline(admin.TabularInline):
    model = LessonStudent
    extra = 0


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["teacher", "subject_type", "date", "duration_minutes", "created_at"]
    list_filter = ["subject_type"]
    inlines = [LessonStudentInline]
