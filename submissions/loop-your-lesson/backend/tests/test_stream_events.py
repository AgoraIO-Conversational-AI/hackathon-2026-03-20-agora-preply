from stream.events import (
    CompleteEvent,
    ConversationEvent,
    ErrorEvent,
    StatusEvent,
    StreamChunkEvent,
    StreamEventType,
    ToolResultEvent,
    ToolStartEvent,
)
from stream.sse import serialize_sse


class TestStreamEvents:
    def test_conversation_event(self):
        e = ConversationEvent.create("conv-123")
        assert e.type == StreamEventType.CONVERSATION
        data = e.to_sse_data()
        assert data["conversation_id"] == "conv-123"

    def test_status_event(self):
        e = StatusEvent.create("Thinking...")
        data = e.to_sse_data()
        assert data["message"] == "Thinking..."

    def test_stream_chunk_event(self):
        e = StreamChunkEvent.create("Hello world")
        data = e.to_sse_data()
        assert data["content"] == "Hello world"

    def test_tool_start_event(self):
        e = ToolStartEvent.create("query_lesson_errors", {"type": "grammar"}, "tc_1")
        data = e.to_sse_data()
        assert data["tool_name"] == "query_lesson_errors"
        assert data["tool_id"] == "tc_1"
        assert data["tool_input"] == {"type": "grammar"}

    def test_tool_result_event(self):
        e = ToolResultEvent.create("query_lesson_errors", "Found 3", {"errors": []}, "tc_1", 150)
        data = e.to_sse_data()
        assert data["tool_name"] == "query_lesson_errors"
        assert data["execution_time_ms"] == 150
        assert data["data"] == {"errors": []}

    def test_complete_event_with_usage(self):
        e = CompleteEvent.create("end_turn", 100, 50, cost_usd=0.001)
        data = e.to_sse_data()
        assert data["usage"]["input_tokens"] == 100
        assert data["usage"]["output_tokens"] == 50
        assert data["usage"]["cost_usd"] == 0.001

    def test_complete_event_without_cost(self):
        e = CompleteEvent.create("end_turn", 100, 50)
        data = e.to_sse_data()
        assert "cost_usd" not in data["usage"]

    def test_error_event(self):
        e = ErrorEvent.create("Something failed", code="test_error")
        data = e.to_sse_data()
        assert data["message"] == "Something failed"
        assert data["code"] == "test_error"


class TestSSESerialization:
    def test_serialize_sse_format(self):
        e = StatusEvent.create("Processing...")
        result = serialize_sse(e)
        assert result.startswith("event: status\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_serialize_sse_with_msg_id(self):
        e = StatusEvent.create("Test")
        result = serialize_sse(e, msg_id="1234-0")
        assert result.startswith("id: 1234-0\n")
        assert "event: status\n" in result

    def test_serialize_sse_contains_json_payload(self):
        e = StreamChunkEvent.create("hello")
        result = serialize_sse(e)
        assert '"content": "hello"' in result
