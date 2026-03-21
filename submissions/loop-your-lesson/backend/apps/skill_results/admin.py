from django.contrib import admin

from apps.skill_results.models import SkillExecution


@admin.register(SkillExecution)
class SkillExecutionAdmin(admin.ModelAdmin):
    list_display = ["skill_name", "status", "teacher", "lesson", "student", "created_at"]
    list_filter = ["status", "skill_name"]
