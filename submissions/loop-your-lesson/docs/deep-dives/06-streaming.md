# Streaming

> Inspired by [PostHog's Max AI assistant](https://github.com/PostHog/posthog).
> Source: [`ee/hogai/core/stream_processor.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/stream_processor.py), [`ee/hogai/core/executor.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/executor.py)

## At a glance

**What this covers**: The three-layer streaming pattern (Temporal activity → Redis Streams → SSE) that delivers AI responses to the frontend in real time, with message merging and progressive trust disclosure.

**Why it matters**: Streaming builds trust. Users see the AI's reasoning and data access as it happens, not just the final answer.

**Key terms**:

| Term | Meaning |
|------|---------|
| SSE | Server-Sent Events - one-way server→client stream over HTTP |
| Event types | STATUS, THINKING, TOOL_START, TOOL_RESULT, STREAM, COMPLETE, ERROR |
| Message merging | Update existing messages by ID instead of appending new ones (upsertMessage pattern) |
| Last-Event-ID | SSE header for reconnection - resume from where you left off |
| Trust layers | Each event type maps to a trust level: WHY (thinking), WHAT (tool start), WHERE (tool result) |

**Prerequisites**: [agent-loop.md](04-agent-loop.md)

---

## What PostHog does

PostHog streams AI assistant responses through three layers: Temporal
workflows produce events, Redis Streams buffer them, and Django async
views deliver them as SSE to the browser.

### StreamProcessor protocol

Defines which LangGraph nodes emit events to the client:

```python
# ee/hogai/core/stream_processor.py
class AssistantStreamProcessorProtocol(Protocol[T]):
    _team: Team
    _user: User
    _streamed_update_ids: set[str]

    def process(self, event: AssistantDispatcherEvent) -> Coroutine[Any, Any, list[T] | None]:
        ...

    def process_langgraph_update(self, event: LangGraphUpdateEvent) -> Coroutine[Any, Any, list[T] | None]:
        ...

    def mark_id_as_streamed(self, message_id: str) -> None:
        self._streamed_update_ids.add(message_id)
```

`_streamed_update_ids` prevents duplicate delivery -- if a reconnecting
client replays from a past offset, already-sent messages are skipped.

### Redis Streams as buffer

[`ConversationRedisStream`](https://github.com/PostHog/posthog/blob/master/ee/hogai/stream/redis_stream.py)
decouples the Temporal producer from the Django consumer:

```python
# ee/hogai/stream/redis_stream.py
CONVERSATION_STREAM_MAX_LENGTH = 1000
CONVERSATION_STREAM_CONCURRENT_READ_COUNT = 8
CONVERSATION_STREAM_TIMEOUT = 30 * 60  # 30 minutes

async def write_to_stream(self, generator, callback=None, emit_completion=True):
    await self._redis_client.expire(self._stream_key, self._timeout)
    async for chunk in generator:
        message = self._serializer.dumps(chunk)
        if message is not None:
            await self._redis_client.xadd(
                self._stream_key,
                message,
                maxlen=self._max_length,
                approximate=True,
            )
    if emit_completion:
        await self._write_status(StatusPayload(status="complete"))

async def read_stream(self, start_id="0", block_ms=50, count=8):
    current_id = start_id
    while True:
        messages = await self._redis_client.xread(
            {self._stream_key: current_id},
            block=block_ms,
            count=count,
        )
        if not messages:
            continue
        for _, stream_messages in messages:
            for stream_id, message in stream_messages:
                current_id = stream_id
                data = self._serializer.deserialize(message)
                REDIS_TO_CLIENT_LATENCY_HISTOGRAM.observe(time.time() - data.timestamp)
                if isinstance(data.event, StreamStatusEvent):
                    if data.event.payload.status == "complete":
                        return
                    elif data.event.payload.status == "error":
                        raise StreamError(data.event.payload.error)
                else:
                    yield data
```

`XADD` with `maxlen=1000` caps memory. `XREAD` with `block=50ms` polls
without busy-waiting. Each `StreamEvent` carries a `timestamp` field
(set at write time) so the consumer can measure end-to-end latency.

### Reconnection support

The [`AgentExecutor`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/executor.py)
checks conversation status on entry. If the conversation is already
running, it resumes from the existing Redis stream instead of starting
a new workflow:

```python
# ee/hogai/core/executor.py
async def astream(self, workflow, inputs):
    if self._conversation.status != Conversation.Status.IDLE and self._reconnectable:
        if hasattr(inputs, "message") and inputs.message is not None:
            raise ValueError("Cannot resume streaming with a new message")
        async for chunk in self.stream_conversation():
            yield chunk
    else:
        async for chunk in self.start_workflow(workflow, inputs):
            yield chunk
```

Because Redis Streams are ordered and `XREAD` accepts a `start_id`,
a reconnecting client picks up exactly where it left off.

### Latency histograms

Four Prometheus histograms track streaming health:

| Metric | What it measures |
|--------|-----------------|
| `redis_to_client_latency` | Time from XADD to XREAD (end-to-end) |
| `redis_read_iteration_latency` | Read loop iteration time |
| `redis_write_iteration_latency` | Write loop iteration time |
| `stream_init_iteration_latency` | Waiting for stream creation |

### Event type routing

`AgentExecutor` converts Redis stream events to typed output:

```python
# ee/hogai/core/executor.py
async def _redis_stream_to_assistant_output(self, message):
    if isinstance(message.event, MessageEvent):
        return (AssistantEventType.MESSAGE, message.event.payload)
    elif isinstance(message.event, ConversationEvent):
        conversation = await Conversation.objects.aget(id=message.event.payload)
        return (AssistantEventType.CONVERSATION, conversation)
    elif isinstance(message.event, UpdateEvent):
        return (AssistantEventType.UPDATE, message.event.payload)
    elif isinstance(message.event, GenerationStatusEvent):
        return (AssistantEventType.STATUS, message.event.payload)
    else:
        return None
```

---

## What we take

### Three-layer streaming (matching Medallion)

```
View → Temporal ChatAgentWorkflow → Redis Stream → SSE to frontend
```

**Layer 1: Producer** - Temporal activity runs the agent loop, writes events to Redis via `StreamWriter`:
```python
@activity.defn
async def run_chat_agent(input: ChatAgentInput) -> None:
    writer = StreamWriter(input.conversation_id)
    await writer.connect()

    async for event in agent.run(input.message, conversation=conversation):
        await writer.write(event)
        activity.heartbeat()

    await writer.close()
```

**Layer 2: Buffer** - Redis Streams with XADD/XREAD:
```python
class StreamWriter:
    async def write(self, event: StreamEvent) -> None:
        await self._redis.xadd(
            self._stream_key,
            {"data": event.serialize()},
            maxlen=1000,
        )

class StreamReader:
    async def read(self, last_id: str = "0") -> AsyncGenerator[StreamEvent, None]:
        while True:
            entries = await self._redis.xread(
                {self._stream_key: last_id}, block=50, count=10,
            )
            for entry_id, data in entries:
                last_id = entry_id
                yield StreamEvent.deserialize(data["data"])
```

**Layer 3: Consumer** - Django view reads Redis, pipes to SSE:
```python
async def conversation_stream_view(request, conversation_id):
    # Start Temporal workflow (non-blocking)
    await start_chat_workflow(conversation_id, message)

    # Read from Redis, pipe to SSE
    reader = StreamReader(conversation_id)
    response = StreamingHttpResponse(
        streaming_content=sse_generator(reader),
        content_type="text/event-stream",
    )
    return response
```

### Event types

Six event types, each serving a trust-disclosure purpose:

| Event | Payload | Trust layer |
|-------|---------|-------------|
| `STATUS` | `{"message": "Loading..."}` | Progress indicator |
| `THINKING` | `{"content": "Pulling Maria's report..."}` | Layer 1: shows WHY |
| `TOOL_START` | `{"tool": "query_errors", "args": {...}}` | Layer 2: shows WHAT |
| `TOOL_RESULT` | `{"message": "...", "data": {...}}` | Layer 3: shows WHERE from |
| `STREAM` | `{"content": "Maria had 4 grammar..."}` | Text chunks |
| `COMPLETE` | `{}` | Turn done |

Progressive disclosure: `THINKING` renders as a collapsible block,
`TOOL_START` as an expandable step, `TOOL_RESULT` as a widget with
source links. The teacher sees the AI's work without being overwhelmed.

### SSE event format

Each event uses the SSE `event:` field for type routing and carries a
JSON payload with an incrementing `id` for reconnection:

```
id: 1
event: status
data: {"message": "Looking up Maria's report..."}

id: 2
event: thinking
data: {"content": "Querying student report: errors, practice results, suggested focus."}

id: 3
event: tool_start
data: {"tool": "query_student_report", "args": {"student_id": "maria_42"}}

id: 4
event: tool_result
data: {"message": "Found 9 errors (4 grammar, 3 vocabulary, 2 pronunciation).", "data": {"widget_type": "error_analysis", "total_errors": 9, "errors": [...]}}

id: 5
event: stream
data: {"content": "Maria"}

id: 6
event: stream
data: {"content": " had a solid lesson"}

id: 7
event: complete
data: {}

```

## Message merging by ID

Borrowed from Medallion's `upsertMessage()` pattern. Instead of appending every
SSE event as a new message, messages update in-place by ID.

**Why it matters**:
- Streaming text: same message grows as chunks arrive (no duplication)
- Tool results: replace "Loading..." placeholder with actual widget
- Thinking steps: accumulate in one block, not N separate messages

**Frontend implementation** (from Medallion's `useChat.ts`):
```typescript
function upsertMessage(messages: Message[], newMsg: Message): Message[] {
    const idx = messages.findIndex((m) => m.id === newMsg.id)
    if (idx >= 0) {
        const updated = [...messages]
        updated[idx] = newMsg
        return updated
    }
    return [...messages, newMsg]
}
```

**Consecutive message merging** - accumulate processSteps and toolResults:
```typescript
// Merge consecutive assistant messages into one bubble
const mergedMessages = useMemo(() => {
    const result: Message[] = []
    for (const msg of messages) {
        const prev = result[result.length - 1]
        if (msg.role === 'assistant' && prev?.role === 'assistant') {
            result[result.length - 1] = {
                ...prev,
                content: msg.content || prev.content,
                processSteps: [...(prev.processSteps ?? []), ...(msg.processSteps ?? [])],
                toolResults: [...(prev.toolResults ?? []), ...(msg.toolResults ?? [])],
            }
        } else {
            result.push({ ...msg })
        }
    }
    return result
}, [messages])
```

**Backend**: every SSE event carries a `message_id`. The UPDATE event type
replaces an existing message by ID. STREAM events append to the message
with the current `message_id`.

### Django async SSE view

The view starts a Temporal workflow (non-blocking) and reads from the
Redis stream, formatting each event as an SSE frame.
`StreamingHttpResponse` with `text/event-stream` content type handles
the HTTP layer:

```python
import json
from collections.abc import AsyncGenerator
from django.http import StreamingHttpResponse

from backend.services.ai_chat.stream import StreamReader


class StreamEventType:
    STATUS = "status"
    THINKING = "thinking"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    STREAM = "stream"
    COMPLETE = "complete"


def format_sse(event_type: str, data: dict, event_id: str) -> str:
    """Format a single SSE frame."""
    return f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_chat(request, conversation_id: str):
    """SSE endpoint for chat streaming."""
    conversation = await get_conversation(conversation_id, request.user)
    last_event_id = request.headers.get("Last-Event-ID", "0")

    # Start Temporal workflow (non-blocking)
    await start_chat_workflow(conversation_id, request.data.get("message"))

    async def event_stream() -> AsyncGenerator[str, None]:
        reader = StreamReader(conversation_id)

        async for event in reader.read(last_id=last_event_id):
            if event.type == "thinking":
                yield format_sse(StreamEventType.THINKING, {"content": event.content}, event.id)

            elif event.type == "tool_start":
                yield format_sse(StreamEventType.TOOL_START, {
                    "tool": event.tool_name,
                    "args": event.tool_args,
                }, event.id)

            elif event.type == "tool_result":
                message, data = event.result
                yield format_sse(StreamEventType.TOOL_RESULT, {
                    "message": message,
                    "data": data,
                }, event.id)

            elif event.type == "stream":
                yield format_sse(StreamEventType.STREAM, {"content": event.content}, event.id)

            elif event.type == "complete":
                yield format_sse(StreamEventType.COMPLETE, {}, event.id)

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
```

### Frontend EventSource consumer

The Chrome extension side panel connects with `EventSource` and routes
events by type through a callback interface:

```typescript
// chrome_extension/src/lib/stream.ts

interface StreamCallbacks {
  onStatus: (message: string) => void
  onThinking: (content: string) => void
  onToolStart: (tool: string, args: Record<string, unknown>) => void
  onToolResult: (message: string, data: Record<string, unknown>) => void
  onStream: (content: string) => void
  onComplete: () => void
  onError: (error: string) => void
}

function connectChat(conversationId: string, callbacks: StreamCallbacks): EventSource {
  const es = new EventSource(`/api/conversations/${conversationId}/chat/`)

  es.addEventListener('thinking', (e) => callbacks.onThinking(JSON.parse(e.data).content))
  es.addEventListener('tool_start', (e) => {
    const { tool, args } = JSON.parse(e.data)
    callbacks.onToolStart(tool, args)
  })
  es.addEventListener('tool_result', (e) => {
    const { message, data } = JSON.parse(e.data)
    callbacks.onToolResult(message, data)
  })
  es.addEventListener('stream', (e) => callbacks.onStream(JSON.parse(e.data).content))
  es.addEventListener('complete', () => { callbacks.onComplete(); es.close() })
  es.onerror = () => { callbacks.onError('Connection lost'); es.close() }

  return es
}
```

### Reconnection via Last-Event-ID

`EventSource` automatically reconnects on disconnect. The browser sends
`Last-Event-ID` with the last received Redis stream ID. The Django view
passes this to `StreamReader.read(last_id=...)`, which resumes from that
offset via `XREAD`. Because Redis Streams are ordered and persistent,
reconnecting clients pick up exactly where they left off - even if the
SSE connection was interrupted mid-stream.

---

## What we skip (and why)

| PostHog feature | Why we skip it |
|-----------------|---------------|
| **Latency histograms** | Add post-hackathon when we have production traffic to measure. For now, browser DevTools network tab is sufficient. |
| **Stream processor protocol** | PostHog needs `_verbose_nodes` and `_streaming_nodes` to filter LangGraph node output. Our agent loop is a flat generator -- every yield goes to the client. No filtering layer needed. |
| **Pickle serialization** | PostHog serializes events with pickle for Redis. We serialize to JSON directly in `StreamEvent.serialize()`. |

---

## Implementation notes

### Where each event is emitted

```
agent_loop():
    yield StatusEvent("Processing your question...")

    # LLM call with streaming
    async for chunk in llm.stream(messages):
        if chunk.type == "thinking":
            yield ThinkingEvent(chunk.content)
        elif chunk.type == "text":
            yield StreamChunkEvent(chunk.content)
        elif chunk.type == "tool_use":
            yield ToolStartEvent(chunk.name, chunk.input)
            message, data = await tool.execute(**chunk.input)
            yield ToolResultEvent((message, data))
            # Append tool result to messages, loop back to LLM
```

### URL routing

```python
# backend/api/urls.py
urlpatterns = [
    path(
        "conversations/<uuid:conversation_id>/chat/",
        stream_chat,
        name="conversation-chat",
    ),
]
```

### ASGI requirement

`StreamingHttpResponse` with async generators requires ASGI. The Django
dev server (`runserver`) supports this natively. For production, use
uvicorn or daphne:

```bash
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000
```

### Chrome extension considerations

Chrome extensions can use `EventSource` from the side panel. The
extension's background service worker handles auth token injection.
`manifest.json` must include the backend origin in `host_permissions`.

### Post-hackathon upgrades

1. **Latency metrics** -- Prometheus histograms mirroring PostHog's
   pattern, once we have production traffic
2. **Cancellation** -- PostHog's `cancel_workflow` pattern adapted to
   cancel the Temporal workflow and signal the Redis stream
3. **Backpressure** -- if the client falls behind, buffer or drop
   `STREAM` chunks (text is reconstructable from the final message)
