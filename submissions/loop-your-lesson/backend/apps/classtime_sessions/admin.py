from django.contrib import admin

from apps.classtime_sessions.models import ClasstimeSession, SessionParticipant


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0


@admin.register(ClasstimeSession)
class ClasstimeSessionAdmin(admin.ModelAdmin):
    list_display = ["session_code", "session_type", "teacher", "lesson", "status", "created_at"]
    list_filter = ["session_type", "status"]
    inlines = [SessionParticipantInline]
