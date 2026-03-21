"""Agora ConvoAI REST API client.

Manages voice practice agents: start, stop, update context, speak.
Uses native Claude (style: "anthropic") — no custom LLM proxy needed.

Docs: https://docs.agora.io/en/conversational-ai/rest-api/agent/join
"""

import base64
import logging
from typing import Any

import httpx
from django.conf import settings

from services.agora.tokens import generate_rtc_token
from services.convoai.schemas import AgentResponse

logger = logging.getLogger(__name__)

BASE_URL = "https://api.agora.io/api/conversational-ai-agent/v2/projects"

AGENT_UID = "100"
STUDENT_UID = 101  # Must match frontend


class ConvoAIClient:
    """Client for Agora Conversational AI REST API."""

    def __init__(self) -> None:
        self.app_id: str = settings.AGORA_APP_ID
        credentials = base64.b64encode(
            f"{settings.AGORA_CUSTOMER_ID}:{settings.AGORA_CUSTOMER_SECRET}".encode()
        ).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def _base(self) -> str:
        return f"{BASE_URL}/{self.app_id}"

    async def start_agent(
        self,
        *,
        channel: str,
        agent_token: str,
        system_prompt: str,
        greeting: str,
        asr_language: str = "en-US",
    ) -> AgentResponse:
        """Start a ConvoAI agent with OpenAI in the given channel.

        Uses OpenAI (default ConvoAI provider) — no style override needed.
        All hackathon sponsors: Agora + OpenAI + Anam + Thymia.
        Context updates happen via /update and /speak endpoints.
        """
        payload: dict[str, Any] = {
            "name": f"agent_{channel}",
            "properties": {
                "channel": channel,
                "token": agent_token,
                "agent_rtc_uid": AGENT_UID,
                "remote_rtc_uids": [str(STUDENT_UID)],
                "idle_timeout": 300,
                "asr": {"language": asr_language},
                "llm": {
                    "url": "https://api.openai.com/v1/chat/completions",
                    "api_key": settings.OPENAI_API_KEY,
                    "style": "openai",
                    "system_messages": [{"role": "system", "content": system_prompt}],
                    "greeting_message": greeting,
                    "failure_message": "Sorry, could you say that again?",
                    "max_history": 32,
                    "params": {
                        "model": "gpt-4.1",
                    },
                },
                "advanced_features": {"enable_aivad": True},
                "turn_detection": {
                    "mode": "default",
                    "config": {
                        "speech_threshold": 0.6,
                        "start_of_speech": {
                            "mode": "vad",
                            "vad_config": {
                                "interrupt_duration_ms": 500,
                                "speaking_interrupt_duration_ms": 500,
                                "prefix_padding_ms": 800,
                            },
                        },
                        "end_of_speech": {
                            "mode": "semantic",
                            "semantic_config": {
                                "silence_duration_ms": 600,
                                "max_wait_ms": 5000,
                            },
                        },
                    },
                },
                "tts": {
                    "vendor": "elevenlabs",
                    "params": {
                        "key": settings.ELEVENLABS_API_KEY,
                        "model_id": "eleven_flash_v2_5",
                        "voice_id": settings.ELEVENLABS_VOICE_ID,
                        "sample_rate": 24000,
                    },
                },
                "parameters": {
                    "silence_config": {
                        "timeout_ms": 15000,
                        "action": "speak",
                        "content": "Take your time — there's no rush. What were you thinking about?",
                    },
                },
                "filler_words": {
                    "enable": True,
                    "trigger": {
                        "mode": "fixed_time",
                        "fixed_time_config": {"response_wait_ms": 1500},
                    },
                    "content": {
                        "mode": "static",
                        "static_config": {
                            "phrases": ["Hmm, let me think...", "Good question!", "Okay..."],
                            "selection_rule": "shuffle",
                        },
                    },
                },
            },
        }

        # Add video avatar if configured (Anam via Agora ConvoAI native support)
        if settings.AVATAR_API_KEY:
            avatar_uid = "200"
            avatar_token = generate_rtc_token(channel, int(avatar_uid))
            payload["properties"]["avatar"] = {
                "vendor": settings.AVATAR_VENDOR or "anam",
                "enable": True,
                "params": {
                    "api_key": settings.AVATAR_API_KEY,
                    "agora_uid": avatar_uid,
                    "agora_token": avatar_token,
                    "avatar_id": settings.AVATAR_ID,
                    "sample_rate": 24000,
                },
            }
            logger.info("Avatar enabled: vendor=%s", settings.AVATAR_VENDOR or "anam")

        import json as _json

        logger.info(
            "Starting ConvoAI agent on channel=%s (prompt=%d chars)\nPayload LLM config: %s",
            channel,
            len(system_prompt),
            _json.dumps({k: v for k, v in payload["properties"]["llm"].items() if k != "system_messages"}, indent=2),
        )
        resp = await self._client.post(f"{self._base}/join", headers=self.headers, json=payload)
        if resp.status_code >= 400:
            logger.error("Agora ConvoAI error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Agent started: agent_id=%s status=%s response=%s", data["agent_id"], data["status"], data)
        return AgentResponse.model_validate(data)

    async def stop_agent(self, agent_id: str) -> None:
        """Stop a running agent."""
        logger.info("Stopping agent=%s", agent_id)
        resp = await self._client.post(f"{self._base}/agents/{agent_id}/leave", headers=self.headers)
        resp.raise_for_status()

    async def update_agent(self, agent_id: str, system_prompt: str) -> None:
        """Update system prompt on a running agent (inject quiz results, visual state)."""
        payload: dict[str, Any] = {
            "properties": {"llm": {"system_messages": [{"role": "system", "content": system_prompt}]}}
        }
        logger.info("[CONVOAI_CLIENT] /update request: agent=%s prompt_len=%d", agent_id, len(system_prompt))
        resp = await self._client.post(
            f"{self._base}/agents/{agent_id}/update",
            headers=self.headers,
            json=payload,
        )
        logger.info(
            "[CONVOAI_CLIENT] /update response: agent=%s status=%s body=%s",
            agent_id,
            resp.status_code,
            resp.text[:200],
        )
        resp.raise_for_status()

    async def speak(
        self,
        agent_id: str,
        text: str,
        priority: str = "APPEND",
        interruptable: bool = True,
    ) -> None:
        """Make the agent say something via TTS (bypasses LLM).

        Priority:
          APPEND — queue after current speech (default, no interruption)
          INTERRUPT — stop current speech, say this instead
          IGNORE — skip if already speaking
        """
        logger.info("[CONVOAI_CLIENT] /speak request: agent=%s priority=%s text=%s", agent_id, priority, text[:120])
        resp = await self._client.post(
            f"{self._base}/agents/{agent_id}/speak",
            headers=self.headers,
            json={"text": text, "priority": priority, "interruptable": interruptable},
        )
        logger.info(
            "[CONVOAI_CLIENT] /speak response: agent=%s status=%s body=%s",
            agent_id,
            resp.status_code,
            resp.text[:200],
        )
        resp.raise_for_status()

    async def interrupt(self, agent_id: str) -> None:
        """Stop agent from speaking/thinking immediately."""
        resp = await self._client.post(f"{self._base}/agents/{agent_id}/interrupt", headers=self.headers)
        resp.raise_for_status()

    async def get_status(self, agent_id: str) -> AgentResponse:
        """Query agent status."""
        resp = await self._client.get(f"{self._base}/agents/{agent_id}", headers=self.headers)
        resp.raise_for_status()
        return AgentResponse.model_validate(resp.json())

    async def get_history(self, agent_id: str) -> list[dict]:
        """Get conversation history from the agent (what it said + heard)."""
        resp = await self._client.get(f"{self._base}/agents/{agent_id}/history", headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("messages", resp.json())

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# Module-level singleton — reused across views and quiz_bridge
_default_client: ConvoAIClient | None = None


def get_client() -> ConvoAIClient:
    """Get a ConvoAI client, recreating if the event loop changed.

    Django dev server reloads close the old event loop, making the
    cached httpx.AsyncClient unusable. Always recreate to be safe.
    """
    global _default_client  # noqa: PLW0603
    _default_client = ConvoAIClient()
    return _default_client
