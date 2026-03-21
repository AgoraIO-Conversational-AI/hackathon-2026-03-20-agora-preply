"""Chat agent Temporal workflow.

Adapted from Medallion AI Phone Agent (apps/ai_chat/workflows/chat_agent.py).
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

logger = logging.getLogger("ai_chat")

with workflow.unsafe.imports_passed_through():
    from typing import Any

    from asgiref.sync import sync_to_async

    from apps.conversations.models import Conversation, ConversationManager
    from apps.conversations.services.agent import PreplyAgent
    from apps.conversations.services.context import build_system_prompt
    from apps.conversations.services.context_types import ConversationContext
    from apps.conversations.services.modes import AgentMode, get_mode_config
    from apps.skill_results.models import SkillExecution, SkillExecutionStatus
    from apps.tutoring.models import TutoringRelationship
    from stream.events import ConversationEvent, ErrorEvent
    from stream.redis_stream import StreamWriter


@dataclass
class ChatAgentInput:
    conversation_id: str
    message: str
    mode: str = "daily_briefing"
    teacher_id: str | None = None
    student_id: str | None = None
    lesson_id: str | None = None


@workflow.defn(name="chat-agent")
class ChatAgentWorkflow:
    @workflow.run
    async def run(self, input: ChatAgentInput) -> None:
        await workflow.execute_activity(
            run_chat_agent,
            input,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=2,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )


@activity.defn
async def run_chat_agent(input: ChatAgentInput) -> None:
    writer = StreamWriter(input.conversation_id)
    try:
        await writer.connect()

        conversation = await Conversation.objects.select_related("teacher", "student", "lesson").aget(
            id=input.conversation_id
        )

        # Load existing messages for multi-turn conversations
        existing_messages = await sync_to_async(ConversationManager.get_messages_for_api)(conversation)

        # For follow-up messages, persist and append the new user message
        if existing_messages and input.message:
            await sync_to_async(ConversationManager.add_user_message)(conversation, input.message)
            existing_messages.append({"role": "user", "content": input.message})

        # Build context from conversation's related objects
        is_student_practice = input.mode == AgentMode.STUDENT_PRACTICE
        context: ConversationContext = {}

        if conversation.teacher_id:
            context["teacher"] = {"teacher_name": conversation.teacher.name}

        if conversation.student_id:
            student_ctx: dict[str, Any] = {"student_name": conversation.student.name}
            rel = await sync_to_async(
                TutoringRelationship.objects.filter(
                    student_id=conversation.student_id,
                    teacher_id=conversation.teacher_id,
                ).first
            )()
            if rel:
                student_ctx["level"] = rel.current_level
                student_ctx["goal"] = rel.goal
                context["subject"] = {
                    "subject_type": rel.subject_type,
                    "subject_config": rel.subject_config,
                }
            context["student"] = student_ctx

        if conversation.lesson_id:
            lesson_ctx: dict[str, Any] = {
                "lesson_date": str(conversation.lesson.date),
                "duration": conversation.lesson.duration_minutes,
                "summary": conversation.lesson.transcript_summary,
            }

            if is_student_practice and conversation.lesson.transcript:
                lesson_ctx["transcript"] = conversation.lesson.transcript

            if is_student_practice:
                skill_executions = await sync_to_async(
                    lambda: list(
                        SkillExecution.objects.filter(
                            lesson_id=conversation.lesson_id,
                            status=SkillExecutionStatus.COMPLETED,
                        ).values("skill_name", "output_data")
                    )
                )()
                if skill_executions:
                    lesson_ctx["skill_outputs"] = {se["skill_name"]: se["output_data"] for se in skill_executions}

            context["lesson"] = lesson_ctx

            # Fallback: extract subject from lesson when no relationship
            if "subject" not in context:
                context["subject"] = {
                    "subject_type": conversation.lesson.subject_type,
                    "subject_config": conversation.lesson.subject_config,
                }

        # Build agent
        config = get_mode_config(input.mode)
        tools = [cls() for cls in config.tool_classes]
        system_prompt = build_system_prompt(input.mode, context=context or None)
        agent = PreplyAgent(mode=input.mode, tools=tools, system_prompt=system_prompt)

        await writer.write(ConversationEvent.create(input.conversation_id))

        async for event in agent.stream_response(
            input.message,
            messages=existing_messages if existing_messages else None,
            conversation=conversation,
        ):
            await writer.write(event)
            activity.heartbeat()

    except Exception as e:
        logger.exception("Chat agent activity failed for conversation %s", input.conversation_id)
        await writer.write(ErrorEvent.create(str(e), code="activity_error"))
        raise
    finally:
        await writer.close()
