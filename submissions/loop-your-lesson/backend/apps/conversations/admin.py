from django.contrib import admin

from apps.conversations.models import ApprovalRequest, Conversation, Message, ToolExecution


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["title", "mode", "status", "teacher", "student", "updated_at"]
    list_filter = ["mode", "status"]
    search_fields = ["title"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "role", "content_preview", "created_at"]
    list_filter = ["role"]

    def content_preview(self, obj):
        return obj.content[:80] if obj.content else ""


@admin.register(ToolExecution)
class ToolExecutionAdmin(admin.ModelAdmin):
    list_display = ["tool_name", "success", "execution_time_ms", "conversation", "created_at"]
    list_filter = ["success", "tool_name"]


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["tool_name", "status", "conversation", "created_at"]
    list_filter = ["status"]
