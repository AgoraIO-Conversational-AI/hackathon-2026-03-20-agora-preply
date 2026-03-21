# Agora Conversational AI — Technology Guide

How to create voice AI agents that students can have real-time conversations with.
ConvoAI is core to our project and earns up to +5 bonus points.

---

## 1. Overview

### What ConvoAI does
Real-time voice AI agents running in Agora's cloud. The pipeline:
1. Student speaks into browser mic
2. Audio streams via Agora RTC to the agent
3. Agent runs: ASR (speech-to-text) → LLM → TTS (text-to-speech)
4. Synthesized speech streams back to student

### Architecture
```
Browser (Agora RTC SDK)  ←→  Agora SD-RTN (cloud)  ←→  ConvoAI Agent
                                                         ↕
                                                    ASR → LLM → TTS
                                                         ↕
                                                    Custom LLM Server
                                                    (our middleware)
```

### Two modes

| Mode | Use | Config |
|------|-----|--------|
| Pipeline | Quick start, zero code | Just `PIPELINE_ID` from Agent Builder |
| Custom LLM | Full control (us) | Point `llm.url` to our server |

We use **Custom LLM mode** to inject lesson context into the conversation.

### Rate limits
- Peak Concurrent Users per App ID: **20** (contact support@agora.io to increase)
- REST API: standard rate limiting applies

---

## 2. Authentication

All REST API calls use **HTTP Basic Auth**.

```python
import base64

customer_id = os.environ["AGORA_CUSTOMER_ID"]
customer_secret = os.environ["AGORA_CUSTOMER_SECRET"]
credentials = base64.b64encode(f"{customer_id}:{customer_secret}".encode()).decode()

headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
}
```

Credentials from [Agora Console](https://console.agora.io/) → RESTful API section.

---

## 3. API Reference

### 3.1 Start Agent (Join)

```
POST https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/join
```

**Request body:**
```json
{
  "name": "practice_agent_student_123",
  "properties": {
    "channel": "lesson_42_practice_student_123",
    "token": "<rtc_token_for_agent>",
    "agent_rtc_uid": "100",
    "remote_rtc_uids": ["101"],
    "idle_timeout": 120,
    "advanced_features": {
      "enable_aivad": true
    },
    "asr": {
      "language": "en-US",
      "vendor": "ares"
    },
    "llm": {
      "url": "https://our-custom-llm.example.com/chat/completions",
      "api_key": "",
      "vendor": "custom",
      "style": "openai",
      "system_messages": [
        {
          "role": "system",
          "content": "You are a language practice assistant..."
        }
      ],
      "greeting_message": "Hi Maria! Ready to practice? Let's work on those articles today.",
      "failure_message": "Sorry, I had trouble understanding. Could you say that again?",
      "max_history": 20,
      "params": {
        "model": "gpt-4o-mini",
        "channel": "lesson_42_practice_student_123",
        "app_id": "<app_id>",
        "user_uid": "101",
        "agent_uid": "100"
      }
    },
    "tts": {
      "vendor": "rime",
      "params": {
        "api_key": "<tts_key>",
        "speaker": "astra",
        "modelId": "mistv2"
      }
    }
  }
}
```

**Response (200):**
```json
{
  "agent_id": "1NT29X10YHxxxxxWJOXLYHNYB",
  "create_ts": 1737111452,
  "status": "RUNNING"
}
```

**Key properties:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `channel` | string | Yes | RTC channel name to join |
| `token` | string | Yes | RTC auth token for the agent |
| `agent_rtc_uid` | string | Yes | Agent's UID in channel ("0" = random) |
| `remote_rtc_uids` | array | Yes | User UIDs to subscribe to (max 1 currently) |
| `idle_timeout` | int | No | Seconds before auto-exit after users leave (default: 30) |

**LLM config:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | LLM endpoint (our Custom LLM server) |
| `vendor` | string | `custom` for custom LLM |
| `style` | string | `openai` / `gemini` / `anthropic` / `dify` |
| `system_messages` | array | System prompt messages |
| `greeting_message` | string | Auto-greeting when student joins |
| `failure_message` | string | Fallback on LLM error |
| `max_history` | int | Conversation messages to cache (1-1024, default: 32) |
| `params` | object | Passed through to Custom LLM (we use for channel/app_id/uids) |
| `template_variables` | object | Key-value pairs for `{{variable}}` substitution in prompts |

**ASR vendors:** `ares` (default, no key needed), `microsoft`, `deepgram`, `openai`, `speechmatics`, `assemblyai`, `amazon`, `google`

**TTS vendors:** `microsoft`, `elevenlabs`, `minimax`, `cartesia`, `openai`, `rime`, `fishaudio`, `google`, `amazon`

### 3.2 Stop Agent (Leave)

```
POST https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents/{agentId}/leave
```

No request body. Returns 200 with empty body.

### 3.3 Update Agent (Runtime)

```
POST https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents/{agentId}/update
```

Can update at runtime: `token`, `llm.system_messages`, `llm.params`.

**Important:** Updating `params` OVERWRITES the entire params object. Pass the complete params.

```json
{
  "properties": {
    "llm": {
      "system_messages": [
        {"role": "system", "content": "Updated: student just got articles wrong on quiz. Focus on articles now."}
      ]
    }
  }
}
```

This is how we inject quiz results mid-conversation — update the system prompt.

### 3.4 Query Agent Status

```
GET https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents/{agentId}
```

**Response:**
```json
{
  "agent_id": "...",
  "start_ts": 1735035893,
  "stop_ts": 1735035900,
  "status": "RUNNING"
}
```

**Statuses:** `IDLE` (0), `STARTING` (1), `RUNNING` (2), `STOPPING` (3), `STOPPED` (4), `RECOVERING` (5), `FAILED` (6)

### 3.5 List Agents

```
GET https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents
```

Query params: `channel`, `state` (default: 2=RUNNING), `limit` (default: 20), `cursor`, `from_time`, `to_time`.

### 3.6 Speak (Inject TTS)

```
POST https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents/{agentId}/speak
```

```json
{
  "text": "Let's switch to practicing articles now.",
  "priority": "INTERRUPT",
  "interruptable": true
}
```

Priority: `INTERRUPT` (stop current speech), `APPEND` (queue after current), `IGNORE` (skip if speaking).

### 3.7 Interrupt Agent

```
POST https://api.agora.io/api/conversational-ai-agent/v2/projects/{appid}/agents/{agentId}/interrupt
```

Empty body. Stops agent from speaking/thinking immediately.

---

## 4. Voice Activity Detection

```json
"advanced_features": {
  "enable_aivad": true
},
"turn_detection": {
  "mode": "default",
  "config": {
    "speech_threshold": 0.5,
    "start_of_speech": {
      "mode": "vad",
      "vad_config": {
        "interrupt_duration_ms": 160,
        "speaking_interrupt_duration_ms": 160,
        "prefix_padding_ms": 800
      }
    },
    "end_of_speech": {
      "mode": "semantic",
      "semantic_config": {
        "silence_duration_ms": 320,
        "max_wait_ms": 3000
      }
    }
  }
}
```

Semantic end-of-speech detection waits for the student to finish their thought, not just pause.

---

## 5. Filler Words

Keep conversation natural while the LLM thinks:

```json
"filler_words": {
  "enable": true,
  "trigger": {
    "mode": "fixed_time",
    "fixed_time_config": {"response_wait_ms": 1500}
  },
  "content": {
    "mode": "static",
    "static_config": {
      "phrases": ["Hmm, let me think...", "Good question!", "Okay..."],
      "selection_rule": "shuffle"
    }
  }
}
```

---

## 6. Silence Handling

```json
"parameters": {
  "silence_config": {
    "timeout_ms": 10000,
    "action": "speak",
    "content": "Are you still there? Take your time — there's no rush."
  },
  "farewell_config": {
    "graceful_enabled": true,
    "graceful_timeout_seconds": 30
  }
}
```

---

## 7. Python Client (copy-pasteable)

```python
"""Agora ConvoAI client for Django backend.

Place at: backend/services/convoai/client.py
"""
import base64
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.agora.io/api/conversational-ai-agent/v2/projects"


@dataclass
class AgentResponse:
    agent_id: str
    status: str
    create_ts: int | None = None


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
        token: str,
        agent_uid: str = "100",
        user_uid: str = "101",
        system_prompt: str,
        greeting: str,
        custom_llm_url: str,
        tts_vendor: str = "rime",
        tts_params: dict[str, Any] | None = None,
        asr_language: str = "en-US",
    ) -> AgentResponse:
        """Start a ConvoAI agent in the given channel."""
        payload = {
            "name": f"agent_{channel}",
            "properties": {
                "channel": channel,
                "token": token,
                "agent_rtc_uid": agent_uid,
                "remote_rtc_uids": [user_uid],
                "idle_timeout": 120,
                "advanced_features": {"enable_aivad": True},
                "asr": {"language": asr_language, "vendor": "ares"},
                "llm": {
                    "url": custom_llm_url,
                    "vendor": "custom",
                    "style": "openai",
                    "system_messages": [{"role": "system", "content": system_prompt}],
                    "greeting_message": greeting,
                    "failure_message": "Sorry, could you repeat that?",
                    "max_history": 20,
                    "params": {
                        "model": "gpt-4o-mini",
                        "channel": channel,
                        "app_id": self.app_id,
                        "user_uid": user_uid,
                        "agent_uid": agent_uid,
                    },
                },
                "tts": {
                    "vendor": tts_vendor,
                    "params": tts_params or {
                        "api_key": settings.TTS_KEY,
                        "speaker": settings.TTS_VOICE_ID,
                        "modelId": "mistv2",
                    },
                },
            },
        }
        resp = await self._client.post(
            f"{self._base}/join", headers=self.headers, json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        return AgentResponse(
            agent_id=data["agent_id"],
            status=data["status"],
            create_ts=data.get("create_ts"),
        )

    async def stop_agent(self, agent_id: str) -> None:
        """Stop a running agent."""
        resp = await self._client.post(
            f"{self._base}/agents/{agent_id}/leave", headers=self.headers
        )
        resp.raise_for_status()

    async def update_agent(
        self, agent_id: str, *, system_prompt: str | None = None
    ) -> None:
        """Update agent config at runtime (e.g., inject quiz results)."""
        payload: dict[str, Any] = {"properties": {}}
        if system_prompt:
            payload["properties"]["llm"] = {
                "system_messages": [{"role": "system", "content": system_prompt}]
            }
        resp = await self._client.post(
            f"{self._base}/agents/{agent_id}/update",
            headers=self.headers,
            json=payload,
        )
        resp.raise_for_status()

    async def speak(
        self,
        agent_id: str,
        text: str,
        priority: str = "APPEND",
        interruptable: bool = True,
    ) -> None:
        """Make the agent say something."""
        resp = await self._client.post(
            f"{self._base}/agents/{agent_id}/speak",
            headers=self.headers,
            json={
                "text": text,
                "priority": priority,
                "interruptable": interruptable,
            },
        )
        resp.raise_for_status()

    async def get_status(self, agent_id: str) -> AgentResponse:
        """Query agent status."""
        resp = await self._client.get(
            f"{self._base}/agents/{agent_id}", headers=self.headers
        )
        resp.raise_for_status()
        data = resp.json()
        return AgentResponse(agent_id=data["agent_id"], status=data["status"])

    async def list_agents(self, channel: str | None = None) -> list[dict[str, Any]]:
        """List agents, optionally filtered by channel."""
        params: dict[str, Any] = {}
        if channel:
            params["channel"] = channel
        resp = await self._client.get(
            f"{self._base}/agents", headers=self.headers, params=params
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("list", [])
```

---

## 8. Token Generation (Python)

```python
"""RTC token generation for Agora.

Place at: backend/services/agora/tokens.py
Requires: pip install agora-token
"""
from agora_token.RtcTokenBuilder2 import RtcTokenBuilder, Role_Publisher
from django.conf import settings

TOKEN_EXPIRY_SECONDS = 86400  # 24 hours


def generate_rtc_token(
    channel_name: str,
    uid: int | str,
    role: int = Role_Publisher,
) -> str:
    """Generate an RTC token for joining a channel."""
    return RtcTokenBuilder.build_token_with_uid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        role,
        token_expire=TOKEN_EXPIRY_SECONDS,
        privilege_expire=TOKEN_EXPIRY_SECONDS,
    )
```

---

## 9. Environment Variables

```bash
# Required — from Agora Console
AGORA_APP_ID=your_app_id                    # Project > App ID
AGORA_APP_CERTIFICATE=your_app_certificate  # Project > App Certificate

# Required — from Agora Console > RESTful API
AGORA_CUSTOMER_ID=your_customer_id
AGORA_CUSTOMER_SECRET=your_customer_secret

# TTS provider (we use Rime)
TTS_VENDOR=rime
TTS_KEY=your_rime_api_key
TTS_VOICE_ID=astra

# Custom LLM server URL (our middleware)
CUSTOM_LLM_URL=https://our-server.example.com/chat/completions
```

---

## 10. Error Codes

| HTTP | Code | Meaning | Action |
|------|------|---------|--------|
| 400 | `InvalidRequest` | Bad request params | Check payload |
| 403 | `InvalidPermission` | ConvoAI not activated | Enable in Agora Console |
| 404 | `TaskNotFound` | Agent not found or exited | Agent already stopped |
| 409 | `TaskConflict` | Agent with same name exists | Use unique names per session |
| 422 | `ResourceQuotaLimitExceeded` | Hit PCU limit (20) | Wait or contact support |
| 503 | `ServiceUnavailable` | Startup failure | Retry with backoff |

---

## 11. Quick Start (for our project)

1. Get credentials from [Agora Console](https://console.agora.io/)
2. Set env vars in `.env`
3. Generate RTC tokens (one for student browser, one for agent)
4. Student joins channel via RTC SDK in browser
5. Backend calls `POST .../join` with Custom LLM URL
6. Agent joins channel, greets student, conversation begins
7. When done, backend calls `POST .../leave`

---

## References

- [ConvoAI Product Overview](https://docs.agora.io/en/conversational-ai/overview/product-overview)
- [REST API Reference](https://docs.agora.io/en/conversational-ai/rest-api/join)
- [Custom LLM Integration](https://docs.agora.io/en/conversational-ai/develop/custom-llm)
- [agent-samples repo](https://github.com/AgoraIO-Conversational-AI/agent-samples)
