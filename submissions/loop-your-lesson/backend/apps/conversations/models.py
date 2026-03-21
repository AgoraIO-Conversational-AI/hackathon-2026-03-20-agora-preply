"""Conversation persistence models.

Adapted from Medallion AI Phone Agent (apps/ai_chat/models.py).
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL_RESULT = "tool_result", "Tool Result"


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Conversation(TimeStampedModel):
    teacher = models.ForeignKey(
        "accounts.Teacher",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conversations",
    )
    mode = models.CharField(max_length=30, default="daily_briefing")
    lesson = models.ForeignKey(
        "lessons.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    status = models.CharField(
        max_length=32,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
    )
    status_metadata = models.JSONField(default=dict, blank=True)
    title = models.CharField(max_length=255, blank=True, default="")

    total_input_tokens = models.IntegerField(default=0)
    total_output_tokens = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.id})"

    def add_tokens(self, input_tokens, output_tokens, cost_usd=0):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += Decimal(str(cost_usd))
        self.save(update_fields=["total_input_tokens", "total_output_tokens", "total_cost_usd", "updated_at"])

    def generate_title(self):
        if self.title:
            return self.title
        first_user_msg = self.messages.filter(role="user").order_by("created_at").first()
        if first_user_msg:
            content = first_user_msg.content[:50]
            if len(first_user_msg.content) > 50:
                content += "..."
            self.title = content
            self.save(update_fields=["title", "updated_at"])
            return self.title
        return "New Conversation"


class Message(TimeStampedModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices, db_index=True)
    content = models.TextField(blank=True, default="")

    tool_calls = models.JSONField(blank=True, null=True)
    tool_use_id = models.CharField(max_length=100, blank=True, null=True)
    tool_name = models.CharField(max_length=100, blank=True, null=True)

    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    stop_reason = models.CharField(max_length=50, blank=True, null=True)
    model_used = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:50] if self.content else ""
        return f"{self.role}: {preview}..."

    def to_api_format(self):
        """Convert to Claude API message format."""
        if self.role == "user":
            if self.tool_use_id:
                return {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": self.tool_use_id,
                            "content": self.content,
                        }
                    ],
                }
            return {"role": "user", "content": self.content}

        elif self.role == "assistant":
            content = []
            if self.content:
                content.append({"type": "text", "text": self.content})
            if self.tool_calls:
                for tc in self.tool_calls:
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["input"],
                        }
                    )
            if not content:
                content.append({"type": "text", "text": ""})
            return {"role": "assistant", "content": content}

        elif self.role == "tool_result":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": self.tool_use_id,
                        "content": self.content,
                    }
                ],
            }

        return {"role": self.role, "content": self.content}


class ToolExecution(TimeStampedModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="tool_executions",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="tool_executions",
        null=True,
        blank=True,
    )
    tool_name = models.CharField(max_length=100, db_index=True)
    tool_use_id = models.CharField(max_length=100)
    input_args = models.JSONField(default=dict)

    success = models.BooleanField(default=True)
    result_message = models.TextField(blank=True, default="")
    result_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    execution_time_ms = models.IntegerField(default=0)
    requires_approval = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "tool_name"]),
        ]

    def __str__(self):
        status = "success" if self.success else "failed"
        return f"{self.tool_name} ({status})"


class ApprovalRequest(TimeStampedModel):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    tool_execution = models.OneToOneField(
        ToolExecution,
        on_delete=models.CASCADE,
        related_name="approval_request",
        null=True,
        blank=True,
    )
    tool_name = models.CharField(max_length=100, db_index=True)
    tool_input = models.JSONField(default=dict)
    description = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approved_by = models.CharField(max_length=50, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Approval for {self.tool_name} ({self.status})"

    def approve(self, user_id="default"):
        self.status = ApprovalStatus.APPROVED
        self.approved_by = user_id
        self.responded_at = timezone.now()
        self.save()
        self.conversation.status = ConversationStatus.ACTIVE
        self.conversation.status_metadata.pop("approval_id", None)
        self.conversation.save()

    def reject(self, user_id="default", reason=""):
        self.status = ApprovalStatus.REJECTED
        self.approved_by = user_id
        self.rejection_reason = reason
        self.responded_at = timezone.now()
        self.save()
        self.conversation.status = ConversationStatus.ACTIVE
        self.conversation.status_metadata.pop("approval_id", None)
        self.conversation.save()

    @property
    def is_pending(self):
        return self.status == ApprovalStatus.PENDING


class ConversationManager:
    """Manager class for conversation DB operations.

    Adapted from Medallion's ConversationManager pattern.
    """

    @staticmethod
    def create_conversation(mode="daily_briefing", teacher=None, student=None, lesson=None):
        return Conversation.objects.create(
            mode=mode,
            teacher=teacher,
            student=student,
            lesson=lesson,
        )

    @staticmethod
    def add_user_message(conversation, content):
        return Message.objects.create(
            conversation=conversation,
            role="user",
            content=content,
        )

    @staticmethod
    def add_assistant_message(
        conversation,
        content,
        tool_calls=None,
        input_tokens=0,
        output_tokens=0,
        stop_reason=None,
        model_used=None,
        cost_usd=0,
        metadata=None,
    ):
        message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=stop_reason,
            model_used=model_used,
            metadata=metadata,
        )
        if input_tokens or output_tokens:
            conversation.add_tokens(input_tokens, output_tokens, cost_usd)
        return message

    @staticmethod
    def add_tool_result(conversation, tool_use_id, tool_name, content):
        return Message.objects.create(
            conversation=conversation,
            role="tool_result",
            content=content,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
        )

    @staticmethod
    def record_tool_execution(
        conversation,
        message,
        tool_name,
        tool_use_id,
        input_args,
        success,
        result_message,
        result_data=None,
        error_message=None,
        execution_time_ms=0,
        requires_approval=False,
    ):
        return ToolExecution.objects.create(
            conversation=conversation,
            message=message,
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            input_args=input_args,
            success=success,
            result_message=result_message,
            result_data=result_data,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            requires_approval=requires_approval,
        )

    @staticmethod
    def get_messages_for_api(conversation):
        """Get all messages formatted for Claude API, with tool results batched."""
        messages = []
        pending_tool_results = []

        for msg in conversation.messages.order_by("created_at"):
            if msg.role == "tool_result":
                pending_tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": msg.tool_use_id,
                        "content": msg.content,
                    }
                )
            else:
                if pending_tool_results:
                    messages.append({"role": "user", "content": pending_tool_results})
                    pending_tool_results = []
                messages.append(msg.to_api_format())

        if pending_tool_results:
            messages.append({"role": "user", "content": pending_tool_results})

        return messages

    @staticmethod
    def get_recent_conversations(teacher=None, student=None, limit=20):
        qs = Conversation.objects.select_related("teacher", "student", "lesson")
        if teacher:
            qs = qs.filter(teacher=teacher)
        if student:
            qs = qs.filter(student=student)
        return list(qs.order_by("-updated_at")[:limit])
