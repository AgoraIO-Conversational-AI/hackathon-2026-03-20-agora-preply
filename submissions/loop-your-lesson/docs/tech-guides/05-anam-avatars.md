# Anam AI Video Avatars — Technology Guide

Real-time video avatar with lip-sync for visual presence during voice practice.
The student sees a face speaking, not just hears audio.

---

## 1. Overview

Anam provides WebRTC-streamed video avatars. You configure a "persona"
(avatar appearance + voice + LLM), get a session token, and stream the
avatar to an HTML `<video>` element.

### How it fits our project

```
Student's browser
    ├── Agora RTC: mic audio → ConvoAI agent (conversation logic)
    │                        ← agent TTS audio ←
    │
    └── Anam SDK: receives agent audio → renders lip-synced avatar video
```

The avatar is purely visual — the conversation logic lives in ConvoAI.
Anam adds the face.

---

## 2. Authentication

### Step 1: Server-side — get session token

```python
"""Anam session token generation.

Place at: backend/services/anam/client.py
"""
import httpx
from django.conf import settings

ANAM_API_URL = "https://api.anam.ai/v1"


async def create_anam_session(
    system_prompt: str = "You are a language practice assistant.",
    avatar_id: str | None = None,
    voice_id: str | None = None,
    language: str = "en",
    max_duration: int = 1800,
) -> str:
    """Create an Anam session and return the session token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ANAM_API_URL}/auth/session-token",
            headers={
                "Authorization": f"Bearer {settings.ANAM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personaConfig": {
                    "name": "Language Practice Avatar",
                    "avatarId": avatar_id or "30fa96d0-26c4-4e55-94a0-517025942e18",
                    "voiceId": voice_id or "6bfbe25a-979d-40f3-a92b-5394170af54b",
                    "llmId": "0934d97d-0c3a-4f33-91b0-5e136a0ef466",
                    "systemPrompt": system_prompt,
                    "languageCode": language,
                    "maxSessionLengthSeconds": max_duration,
                }
            },
        )
        resp.raise_for_status()
        return resp.json()["sessionToken"]
```

Session tokens are valid for **1 hour**.

### Step 2: Client-side — stream avatar

```bash
npm install @anam-ai/js-sdk
```

```tsx
import { createClient, AnamEvent } from "@anam-ai/js-sdk";
import { useEffect, useRef, useState } from "react";

interface AnamAvatarProps {
  sessionToken: string;
}

export function AnamAvatar({ sessionToken }: AnamAvatarProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isReady, setIsReady] = useState(false);
  const clientRef = useRef<any>(null);

  useEffect(() => {
    if (!sessionToken || !videoRef.current) return;

    const anamClient = createClient(sessionToken);
    clientRef.current = anamClient;

    anamClient.addListener(AnamEvent.CONNECTION_ESTABLISHED, () => {
      console.log("Anam connected");
    });

    anamClient.addListener(AnamEvent.VIDEO_PLAY_STARTED, () => {
      setIsReady(true);
    });

    anamClient.addListener(AnamEvent.MESSAGE_HISTORY_UPDATED, (messages: any[]) => {
      console.log("Conversation:", messages);
    });

    anamClient.streamToVideoElement("avatar-video");

    return () => {
      anamClient.stopStreaming?.();
    };
  }, [sessionToken]);

  return (
    <div className="relative">
      <video
        id="avatar-video"
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full rounded-lg"
      />
      {!isReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/50 rounded-lg">
          <p className="text-white">Loading avatar...</p>
        </div>
      )}
    </div>
  );
}
```

---

## 3. Default Persona IDs

| Component | ID | Description |
|-----------|----|-------------|
| Avatar | `30fa96d0-26c4-4e55-94a0-517025942e18` | Cara (default female) |
| Voice | `6bfbe25a-979d-40f3-a92b-5394170af54b` | Default voice |
| LLM | `0934d97d-0c3a-4f33-91b0-5e136a0ef466` | GPT-4.1 Mini |

---

## 4. Persona Configuration

### Voice detection options

```json
{
  "voiceDetectionOptions": {
    "endOfSpeechSensitivity": 0.5,
    "silenceBeforeAutoEndTurnSeconds": 2.0,
    "silenceBeforeSessionEndSeconds": 300,
    "speechEnhancementLevel": 0.5
  }
}
```

### Voice generation options (Cartesia)

```json
{
  "voiceGenerationOptions": {
    "volume": 1.0,
    "speed": 0.9,
    "emotion": "calm"
  }
}
```

Emotions: `neutral`, `calm`, `angry`, `content`, `sad`, `scared`.

---

## 5. SDK Events

| Event | When | Use |
|-------|------|-----|
| `CONNECTION_ESTABLISHED` | WebRTC connected | Show "connected" |
| `VIDEO_PLAY_STARTED` | First frames rendering | Hide loading |
| `MESSAGE_HISTORY_UPDATED` | New message | Update transcript |
| `MESSAGE_STREAM_EVENT_RECEIVED` | Real-time transcription | Live captions |
| `TALK_STREAM_INTERRUPTED` | User interrupted avatar | UI feedback |
| `CONNECTION_CLOSED` | Session ended | Cleanup |

---

## 6. Integration with ConvoAI

### Option A: Anam as visual layer only

ConvoAI handles the full conversation (ASR → LLM → TTS).
Anam receives the TTS audio and renders the avatar.
This is the simpler approach for hackathon.

Configure in ConvoAI join payload:
```json
"avatar": {
  "enable": true,
  "vendor": "anam",
  "params": {
    "api_key": "<anam_api_key>",
    "avatar_id": "<avatar_id>"
  }
}
```

### Option B: Anam with its own LLM (standalone)

Anam handles conversation directly using its built-in LLM integration.
Use this if ConvoAI isn't working or for a simpler demo.

Just create a session token with the system prompt and let Anam handle everything.

---

## 7. Environment Variables

```bash
ANAM_API_KEY=your_anam_api_key        # Server-side only
VIDEO_AVATAR_ID=your_avatar_id        # Optional, defaults to Cara
```

---

## 8. API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/v1/auth/session-token` | Create session (returns token) |
| `GET` | `/v1/voices` | List available voices |
| `POST` | `/v1/tools` | Create a tool (client/webhook/RAG) |
| `PUT` | `/v1/personas/{id}` | Update persona config |

Base URL: `https://api.anam.ai`

---

## References

- [Anam Docs](https://docs.anam.ai)
- [JS SDK](https://www.npmjs.com/package/@anam-ai/js-sdk)
- [agent-samples avatar client](https://github.com/AgoraIO-Conversational-AI/agent-samples/tree/main/react-video-client-avatar)
