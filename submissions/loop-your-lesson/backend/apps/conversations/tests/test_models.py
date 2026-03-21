import pytest

from apps.accounts.models import Teacher
from apps.conversations.models import Conversation, ConversationManager, Message


@pytest.mark.django_db
class TestConversationManager:
    @pytest.fixture
    def db_teacher(self):
        return Teacher.objects.create(name="Test Teacher", email="t@test.com")

    @pytest.fixture
    def db_conversation(self, db_teacher):
        return Conversation.objects.create(mode="daily_briefing", teacher=db_teacher)

    def test_get_messages_for_api_normal_flow(self, db_conversation):
        """User -> Assistant -> done produces correct API format."""
        ConversationManager.add_user_message(db_conversation, "Hello")
        ConversationManager.add_assistant_message(db_conversation, "Hi there!", stop_reason="end_turn")

        messages = ConversationManager.get_messages_for_api(db_conversation)
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Hello"}
        assert messages[1] == {"role": "assistant", "content": [{"type": "text", "text": "Hi there!"}]}

    def test_get_messages_for_api_with_tool_results(self, db_conversation):
        """Tool results are batched as user message with tool_result content blocks."""
        ConversationManager.add_user_message(db_conversation, "Show errors")
        ConversationManager.add_assistant_message(
            db_conversation,
            "",
            tool_calls=[{"id": "tc_1", "name": "query_lesson_errors", "input": {}}],
            stop_reason="tool_use",
        )
        ConversationManager.add_tool_result(db_conversation, "tc_1", "query_lesson_errors", "Found 3 errors")
        ConversationManager.add_assistant_message(db_conversation, "Here are the errors.", stop_reason="end_turn")

        messages = ConversationManager.get_messages_for_api(db_conversation)
        assert len(messages) == 4
        assert messages[0]["role"] == "user"
        # Assistant with tool_use block
        assert messages[1]["role"] == "assistant"
        assert any(b["type"] == "tool_use" for b in messages[1]["content"])
        # Batched tool results as user message
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["tool_use_id"] == "tc_1"
        # Final assistant
        assert messages[3]["role"] == "assistant"

    def test_get_messages_for_api_multiple_tool_results_batched(self, db_conversation):
        """Multiple tool results in sequence are batched into one user message."""
        ConversationManager.add_user_message(db_conversation, "Overview")
        ConversationManager.add_assistant_message(
            db_conversation,
            "",
            tool_calls=[
                {"id": "tc_1", "name": "query_lesson_errors", "input": {}},
                {"id": "tc_2", "name": "query_lesson_themes", "input": {}},
            ],
            stop_reason="tool_use",
        )
        ConversationManager.add_tool_result(db_conversation, "tc_1", "query_lesson_errors", "3 errors")
        ConversationManager.add_tool_result(db_conversation, "tc_2", "query_lesson_themes", "2 themes")

        messages = ConversationManager.get_messages_for_api(db_conversation)
        tool_msg = messages[2]
        assert tool_msg["role"] == "user"
        assert len(tool_msg["content"]) == 2
        assert tool_msg["content"][0]["tool_use_id"] == "tc_1"
        assert tool_msg["content"][1]["tool_use_id"] == "tc_2"

    def test_get_messages_for_api_empty_conversation(self, db_conversation):
        messages = ConversationManager.get_messages_for_api(db_conversation)
        assert messages == []

    def test_generate_title_from_first_message(self, db_conversation):
        ConversationManager.add_user_message(db_conversation, "What errors should I focus on?")
        title = db_conversation.generate_title()
        assert title == "What errors should I focus on?"

    def test_generate_title_truncates_long_messages(self, db_conversation):
        ConversationManager.add_user_message(db_conversation, "A" * 100)
        title = db_conversation.generate_title()
        assert len(title) == 53  # 50 chars + "..."
        assert title.endswith("...")

    def test_generate_title_returns_existing_title(self, db_conversation):
        db_conversation.title = "Already set"
        db_conversation.save()
        assert db_conversation.generate_title() == "Already set"

    def test_generate_title_no_messages(self, db_conversation):
        assert db_conversation.generate_title() == "New Conversation"

    def test_add_tokens_accumulates(self, db_conversation):
        db_conversation.add_tokens(100, 50, 0.001)
        db_conversation.add_tokens(200, 100, 0.002)
        db_conversation.refresh_from_db()
        assert db_conversation.total_input_tokens == 300
        assert db_conversation.total_output_tokens == 150


@pytest.mark.django_db
class TestMessageToApiFormat:
    @pytest.fixture
    def db_conversation(self):
        teacher = Teacher.objects.create(name="T", email="t@t.com")
        return Conversation.objects.create(mode="daily_briefing", teacher=teacher)

    def test_user_message(self, db_conversation):
        msg = Message.objects.create(conversation=db_conversation, role="user", content="Hello")
        assert msg.to_api_format() == {"role": "user", "content": "Hello"}

    def test_assistant_message_with_text(self, db_conversation):
        msg = Message.objects.create(conversation=db_conversation, role="assistant", content="Hi!")
        result = msg.to_api_format()
        assert result["role"] == "assistant"
        assert result["content"] == [{"type": "text", "text": "Hi!"}]

    def test_assistant_message_with_tool_calls(self, db_conversation):
        msg = Message.objects.create(
            conversation=db_conversation,
            role="assistant",
            content="",
            tool_calls=[{"id": "tc_1", "name": "query_lesson_errors", "input": {}}],
        )
        result = msg.to_api_format()
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "tool_use"
        assert result["content"][0]["name"] == "query_lesson_errors"

    def test_assistant_message_with_text_and_tools(self, db_conversation):
        msg = Message.objects.create(
            conversation=db_conversation,
            role="assistant",
            content="Let me check.",
            tool_calls=[{"id": "tc_1", "name": "query_lesson_errors", "input": {}}],
        )
        result = msg.to_api_format()
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "text"
        assert result["content"][1]["type"] == "tool_use"

    def test_assistant_message_empty_content_no_tools(self, db_conversation):
        """Empty assistant message still produces a text block."""
        msg = Message.objects.create(conversation=db_conversation, role="assistant", content="")
        result = msg.to_api_format()
        assert result["content"] == [{"type": "text", "text": ""}]

    def test_tool_result_message(self, db_conversation):
        msg = Message.objects.create(
            conversation=db_conversation,
            role="tool_result",
            content="Found 3 errors",
            tool_use_id="tc_1",
            tool_name="query_lesson_errors",
        )
        result = msg.to_api_format()
        assert result["role"] == "user"
        assert result["content"][0]["type"] == "tool_result"
        assert result["content"][0]["tool_use_id"] == "tc_1"
