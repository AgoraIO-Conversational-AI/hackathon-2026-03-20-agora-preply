from django.contrib import admin

from apps.voice_sessions.models import VoiceSession


@admin.register(VoiceSession)
class VoiceSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "student_id", "lesson_id", "channel", "created_at", "ended_at"]
    list_filter = ["created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
