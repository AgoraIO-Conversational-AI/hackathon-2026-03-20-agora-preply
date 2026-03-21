"""Stream event types for Redis-based message bus.

Adapted from Medallion AI Phone Agent (apps/ai_chat/stream/events.py).
"""

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamEventType(StrEnum):
    CONVERSATION = "conversation"
    STATUS = "status"
    THINKING = "thinking"
    STREAM = "stream"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    APPROVAL = "approval"
    COMPLETE = "complete"
    ERROR = "error"


class StreamEvent(BaseModel):
    type: StreamEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    message_id: str | None = None

    def to_sse_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type.value,
            **self.payload,
        }
        if self.message_id:
            data["message_id"] = self.message_id
        return data


class ConversationEvent(StreamEvent):
    type: StreamEventType = StreamEventType.CONVERSATION

    @classmethod
    def create(cls, conversation_id: str) -> "ConversationEvent":
        return cls(payload={"conversation_id": conversation_id})


class StatusEvent(StreamEvent):
    type: StreamEventType = StreamEventType.STATUS

    @classmethod
    def create(cls, message: str) -> "StatusEvent":
        return cls(payload={"message": message})


class ThinkingEvent(StreamEvent):
    type: StreamEventType = StreamEventType.THINKING

    @classmethod
    def create(cls, content: str) -> "ThinkingEvent":
        return cls(payload={"content": content})


class StreamChunkEvent(StreamEvent):
    type: StreamEventType = StreamEventType.STREAM

    @classmethod
    def create(cls, content: str) -> "StreamChunkEvent":
        return cls(payload={"content": content})


class ToolStartEvent(StreamEvent):
    type: StreamEventType = StreamEventType.TOOL_START

    @classmethod
    def create(
        cls,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_id: str,
        requires_approval: bool = False,
    ) -> "ToolStartEvent":
        return cls(
            payload={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_id": tool_id,
                "requires_approval": requires_approval,
            }
        )


class ToolResultEvent(StreamEvent):
    type: StreamEventType = StreamEventType.TOOL_RESULT

    @classmethod
    def create(
        cls,
        tool_name: str,
        message: str,
        data: dict[str, Any],
        tool_id: str,
        execution_time_ms: int,
    ) -> "ToolResultEvent":
        return cls(
            payload={
                "tool_name": tool_name,
                "message": message,
                "data": data,
                "tool_id": tool_id,
                "execution_time_ms": execution_time_ms,
            }
        )


class ApprovalEvent(StreamEvent):
    type: StreamEventType = StreamEventType.APPROVAL

    @classmethod
    def create(
        cls,
        approval_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        description: str,
    ) -> "ApprovalEvent":
        return cls(
            payload={
                "approval_id": approval_id,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "description": description,
            }
        )


class CompleteEvent(StreamEvent):
    type: StreamEventType = StreamEventType.COMPLETE

    @classmethod
    def create(
        cls,
        stop_reason: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float | None = None,
    ) -> "CompleteEvent":
        usage: dict[str, Any] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        if cost_usd is not None:
            usage["cost_usd"] = round(cost_usd, 6)
        return cls(payload={"stop_reason": stop_reason, "usage": usage})


class ErrorEvent(StreamEvent):
    type: StreamEventType = StreamEventType.ERROR

    @classmethod
    def create(cls, message: str, code: str = "unknown") -> "ErrorEvent":
        return cls(payload={"message": message, "code": code})
