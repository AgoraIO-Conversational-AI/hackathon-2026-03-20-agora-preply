"""SSE serialization and streaming utilities."""

import json
from collections.abc import AsyncGenerator

from django.http import StreamingHttpResponse

from stream.events import StreamEvent, StreamEventType
from stream.redis_stream import ConversationRedisStream


def sse_event(event_type: str, data: dict) -> str:
    """Legacy SSE event formatter."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def sse_response(generator):
    """Create StreamingHttpResponse from a generator."""
    response = StreamingHttpResponse(generator, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def serialize_sse(event: StreamEvent, msg_id: str | None = None) -> str:
    """Convert StreamEvent to SSE wire format."""
    parts = []
    if msg_id:
        parts.append(f"id: {msg_id}")
    parts.append(f"event: {event.type.value}")
    parts.append(f"data: {json.dumps(event.to_sse_data())}")
    return "\n".join(parts) + "\n\n"


async def stream_to_sse(
    stream: ConversationRedisStream,
    last_id: str = "0",
    timeout_seconds: int = 30,
) -> AsyncGenerator[str, None]:
    """Read Redis stream and yield SSE-formatted strings."""
    async for msg_id, event in stream.read_events(last_id=last_id, timeout_seconds=timeout_seconds):
        yield serialize_sse(event, msg_id=msg_id)
        if event.type in (StreamEventType.COMPLETE, StreamEventType.ERROR):
            break


async def stream_conversation(
    conversation_id: str,
    last_id: str = "0",
    timeout_seconds: int = 30,
) -> AsyncGenerator[str, None]:
    """Stream conversation events as SSE. Handles stream lifecycle."""
    async with ConversationRedisStream(conversation_id) as stream:
        async for sse_data in stream_to_sse(stream, last_id, timeout_seconds):
            yield sse_data
