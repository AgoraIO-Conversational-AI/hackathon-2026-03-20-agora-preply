"""Agent loop: while-loop, no framework, no graph.

Adapted from Medallion AI Phone Agent (apps/ai_chat/services/streaming_agent.py).
"""

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import anthropic
from anthropic import NOT_GIVEN
from asgiref.sync import sync_to_async

from apps.conversations.models import ConversationManager
from apps.conversations.services.context import build_system_prompt
from apps.conversations.services.modes import get_mode_config
from apps.conversations.services.tools import PreplyTool
from stream.events import (
    CompleteEvent,
    ErrorEvent,
    StatusEvent,
    StreamChunkEvent,
    StreamEvent,
    ToolResultEvent,
    ToolStartEvent,
)

MAX_ITERATIONS = 10


class PreplyAgent:
    """AI Agent with async streaming.

    Simple agent loop:
    1. Call LLM with tools
    2. If stop_reason == "tool_use": execute tools, yield events, loop
    3. If stop_reason == "end_turn": yield final response, done
    """

    def __init__(
        self,
        mode: str,
        tools: list[PreplyTool] | None = None,
        system_prompt: str | None = None,
    ):
        self.client = anthropic.AsyncAnthropic()
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4096
        self.mode = mode

        if tools is None:
            config = get_mode_config(mode)
            tools = [cls() for cls in config.tool_classes]

        self.tools = tools
        self.tool_map: dict[str, PreplyTool] = {t.name: t for t in tools}
        self.system_prompt = system_prompt or build_system_prompt(mode)

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        definitions = []
        for tool in self.tools:
            schema = tool.args_schema
            json_schema = schema.model_json_schema()
            definitions.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": {
                        "type": "object",
                        "properties": json_schema.get("properties", {}),
                        "required": json_schema.get("required", []),
                    },
                }
            )
        return definitions

    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        conversation=None,
    ) -> tuple[str, Any, int]:
        tool = self.tool_map.get(tool_name)
        if not tool:
            return f"Unknown tool: {tool_name}", {"error": f"Unknown tool: {tool_name}"}, 0

        start_time = time.time()
        try:
            message, data = await tool.execute(conversation=conversation, **tool_input)
            execution_time_ms = int((time.time() - start_time) * 1000)
            return message, data, execution_time_ms
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return f"Tool error: {e!s}", {"error": str(e)}, execution_time_ms

    async def stream_response(
        self,
        user_message: str,
        messages: list[dict[str, Any]] | None = None,
        conversation=None,
    ) -> AsyncGenerator[StreamEvent, None]:
        if messages is None:
            messages = []

        if not messages:
            messages.append({"role": "user", "content": user_message})
            if conversation:
                await sync_to_async(ConversationManager.add_user_message)(conversation, user_message)

        yield StatusEvent.create("Thinking...")

        tool_definitions = self._build_tool_definitions()
        process_steps: list[dict[str, Any]] = []

        for _iteration in range(MAX_ITERATIONS):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,
                    tools=tool_definitions if tool_definitions else NOT_GIVEN,
                    system=self.system_prompt,
                )
            except Exception as e:
                yield ErrorEvent.create(str(e))
                return

            # Extract content blocks
            assistant_content: list[dict[str, Any]] = []
            text_content = ""
            tool_use_blocks = []

            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    tool_use_blocks.append(block)

            messages.append({"role": "assistant", "content": assistant_content})

            # No tool calls -> stream final text
            if response.stop_reason != "tool_use":
                chunk_size = 80
                for i in range(0, len(text_content), chunk_size):
                    yield StreamChunkEvent.create(text_content[i : i + chunk_size])

                if conversation:
                    await sync_to_async(ConversationManager.add_assistant_message)(
                        conversation,
                        content=text_content,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        stop_reason=response.stop_reason,
                        model_used=self.model,
                        metadata={"process_steps": process_steps} if process_steps else None,
                    )

                yield CompleteEvent.create(
                    response.stop_reason,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                return

            # Tool calls - persist assistant message
            assistant_msg = None
            if conversation:
                tool_calls_data = [{"id": tc.id, "name": tc.name, "input": tc.input} for tc in tool_use_blocks]
                assistant_msg = await sync_to_async(ConversationManager.add_assistant_message)(
                    conversation,
                    content=text_content,
                    tool_calls=tool_calls_data,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    stop_reason=response.stop_reason,
                    model_used=self.model,
                )

            # Execute tools
            tool_results = []
            for block in tool_use_blocks:
                tool = self.tool_map.get(block.name)
                process_steps.append(
                    {
                        "type": "tool_call",
                        "toolName": block.name,
                        "toolId": block.id,
                        "toolInput": block.input,
                        "status": "running",
                    }
                )
                yield ToolStartEvent.create(
                    block.name,
                    block.input,
                    block.id,
                    requires_approval=tool.requires_approval if tool else False,
                )

                message, data, exec_ms = await self._execute_tool(block.name, block.input, conversation=conversation)

                yield ToolResultEvent.create(
                    block.name,
                    message,
                    data or {},
                    block.id,
                    exec_ms,
                )

                # Update process step
                for step in reversed(process_steps):
                    if step.get("toolId") == block.id:
                        step["status"] = "failed" if "error" in (data or {}) else "completed"
                        step["result"] = {
                            "message": message,
                            "data": data,
                            "executionTimeMs": exec_ms,
                        }
                        break

                result_content = json.dumps(data) if data else message
                if conversation:
                    await sync_to_async(ConversationManager.add_tool_result)(
                        conversation,
                        block.id,
                        block.name,
                        result_content,
                    )
                    await sync_to_async(ConversationManager.record_tool_execution)(
                        conversation=conversation,
                        message=assistant_msg,
                        tool_name=block.name,
                        tool_use_id=block.id,
                        input_args=block.input,
                        success="error" not in (data or {}),
                        result_message=message,
                        result_data=data,
                        execution_time_ms=exec_ms,
                    )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
            yield StatusEvent.create("Processing results...")

        yield ErrorEvent.create("Exceeded maximum iterations")
