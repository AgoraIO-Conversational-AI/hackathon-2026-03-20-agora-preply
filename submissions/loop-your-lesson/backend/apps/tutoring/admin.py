from django.contrib import admin

from apps.tutoring.models import TutoringRelationship


@admin.register(TutoringRelationship)
class TutoringRelationshipAdmin(admin.ModelAdmin):
    list_display = ["teacher", "student", "subject_type", "current_level", "status", "total_lessons"]
    list_filter = ["status", "subject_type"]
