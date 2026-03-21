from django.contrib import admin

from apps.accounts.models import Student, Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "preply_user_id", "created_at"]
    search_fields = ["name", "email"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "preply_user_id", "created_at"]
    search_fields = ["name", "email"]
