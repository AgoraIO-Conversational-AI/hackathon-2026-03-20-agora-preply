from django.contrib import admin

from apps.daily_briefings.models import DailyBriefing


@admin.register(DailyBriefing)
class DailyBriefingAdmin(admin.ModelAdmin):
    list_display = ["teacher", "date", "generated_at", "created_at"]
    list_filter = ["date"]
