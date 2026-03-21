# Agora RTC & RTM — Technology Guide

Transport layers for audio streaming (RTC) and data messaging (RTM).
RTC carries voice between student and avatar. RTM carries quiz results
to the ConvoAI agent in real-time.

---

## 1. Overview

| Service | Purpose | SDK | Docs |
|---------|---------|-----|------|
| **RTC** (Real-Time Communication) | Audio/video streaming | `agora-rtc-sdk-ng` (Web) | [docs.agora.io/en/video-calling](https://docs.agora.io/en/video-calling/overview/product-overview) |
| **RTM** (Real-Time Messaging / Signaling) | Data messages, presence, channels | `agora-rtm-sdk` (Web) | [docs.agora.io/en/signaling](https://docs.agora.io/en/signaling/overview/product-overview) |

Both use the same **App ID** and **App Certificate** from Agora Console.

### How we use them

```
Student's browser
    │
    ├── RTC: mic audio → Agora cloud → ConvoAI agent (voice conversation)
    │                  ← agent TTS audio ←
    │
    └── RTM: (not directly used by student browser)

Our Django backend
    │
    └── RTM: publish quiz results → channel → Custom LLM Server reads them
```

---

## 2. RTC — Audio Streaming

### Installation

```bash
npm install agora-rtc-sdk-ng
```

### Joining a channel (React)

```typescript
import AgoraRTC, { IAgoraRTCClient, IMicrophoneAudioTrack } from "agora-rtc-sdk-ng";
import { useEffect, useRef, useState } from "react";

interface UseAgoraProps {
  appId: string;
  channel: string;
  token: string;
  uid: number;
}

export function useAgora({ appId, channel, token, uid }: UseAgoraProps) {
  const clientRef = useRef<IAgoraRTCClient | null>(null);
  const localTrackRef = useRef<IMicrophoneAudioTrack | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [remoteAudioReady, setRemoteAudioReady] = useState(false);

  const join = async () => {
    const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
    clientRef.current = client;

    // Listen for agent's audio
    client.on("user-published", async (user, mediaType) => {
      await client.subscribe(user, mediaType);
      if (mediaType === "audio") {
        user.audioTrack?.play();
        setRemoteAudioReady(true);
      }
    });

    client.on("user-unpublished", () => {
      setRemoteAudioReady(false);
    });

    // Join and publish mic
    await client.join(appId, channel, token, uid);
    const localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack();
    localTrackRef.current = localAudioTrack;
    await client.publish([localAudioTrack]);
    setIsConnected(true);
  };

  const leave = async () => {
    localTrackRef.current?.close();
    await clientRef.current?.leave();
    setIsConnected(false);
    setRemoteAudioReady(false);
  };

  useEffect(() => {
    return () => {
      localTrackRef.current?.close();
      clientRef.current?.leave();
    };
  }, []);

  return { join, leave, isConnected, remoteAudioReady };
}
```

### Usage in VoicePractice view

```tsx
function VoicePractice({ appId, channel, token }: Props) {
  const USER_UID = 101; // Fixed UID matching agent config
  const { join, leave, isConnected, remoteAudioReady } = useAgora({
    appId, channel, token, uid: USER_UID,
  });

  return (
    <div>
      {!isConnected ? (
        <button onClick={join}>Start Practice</button>
      ) : (
        <div>
          <p>{remoteAudioReady ? "Avatar is speaking..." : "Connecting to avatar..."}</p>
          <button onClick={leave}>End Practice</button>
        </div>
      )}
    </div>
  );
}
```

---

## 3. RTM — Real-Time Messaging

### Purpose in our project

RTM delivers quiz results from our backend to the Custom LLM Server
so the voice agent can adapt mid-conversation.

```
Classtime quiz → Pusher event → Django backend → RTM publish → channel
                                                                  ↓
                                              Custom LLM Server reads → injects into prompt
```

### Python SDK (server-side)

```bash
pip install agora-rtm
```

### Publishing quiz results

```python
"""RTM client for publishing quiz results to ConvoAI agent.

Place at: backend/services/agora/rtm.py
"""
import json
from agora_token.RtmTokenBuilder2 import RtmTokenBuilder, Role_Rtm_User
from django.conf import settings


def generate_rtm_token(user_id: str) -> str:
    """Generate RTM token for our backend to publish messages."""
    return RtmTokenBuilder.build_token(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        user_id,
        token_expire=86400,   # 24 hours
        privilege_expire=86400,
    )


async def publish_quiz_result(
    channel: str,
    result: dict,
) -> None:
    """Publish a quiz result to the RTM channel.

    The Custom LLM Server subscribes to this channel
    and injects results into the next LLM call.
    """
    # Alternative: call Custom LLM Server directly via HTTP
    # POST {CUSTOM_LLM_URL}/update-quiz-results
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{settings.CUSTOM_LLM_URL}/update-quiz-results",
            json={"channel": channel, "results": [result]},
        )
```

### Quiz result message format

```json
{
  "type": "quiz_result",
  "timestamp": "2026-03-21T10:30:00Z",
  "student_id": "student_123",
  "question": {
    "id": "q_7",
    "type": "GAP",
    "topic": "articles",
    "text": "I went to {0} university yesterday",
    "correct_answer": "a"
  },
  "student_answer": "the",
  "is_correct": false,
  "error_type": "article_confusion"
}
```

---

## 4. Token Generation (Python)

```python
"""Token generation for both RTC and RTM.

Place at: backend/services/agora/tokens.py
"""
from agora_token.RtcTokenBuilder2 import RtcTokenBuilder, Role_Publisher, Role_Subscriber
from agora_token.RtmTokenBuilder2 import RtmTokenBuilder, Role_Rtm_User
from django.conf import settings

TOKEN_EXPIRY = 86400  # 24 hours


def generate_rtc_token(
    channel_name: str,
    uid: int,
    role: int = Role_Publisher,
) -> str:
    """Generate RTC token. Use Role_Publisher for student, Role_Subscriber for viewers."""
    return RtcTokenBuilder.build_token_with_uid(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        channel_name,
        uid,
        role,
        token_expire=TOKEN_EXPIRY,
        privilege_expire=TOKEN_EXPIRY,
    )


def generate_rtm_token(user_id: str) -> str:
    """Generate RTM token for publishing/subscribing to data channels."""
    return RtmTokenBuilder.build_token(
        settings.AGORA_APP_ID,
        settings.AGORA_APP_CERTIFICATE,
        user_id,
        token_expire=TOKEN_EXPIRY,
        privilege_expire=TOKEN_EXPIRY,
    )
```

### Installation

```bash
pip install agora-token
```

---

## 5. Channel Naming Strategy

```
lesson_{lesson_id}_practice_{student_id}
```

Examples:
- `lesson_42_practice_student_123` — Maria's voice practice for lesson 42
- `lesson_42_practice_student_456` — Another student's practice for same lesson

Same channel name used for:
- RTC (student browser ↔ ConvoAI agent audio)
- RTM (backend → Custom LLM Server data messages)
- ConvoAI agent lookup (context.channel in Custom LLM requests)

---

## 6. Quiz → Voice Flow (detailed)

```
1. Student answers Classtime question
     ↓
2. Classtime fires Pusher event: student_response
     ↓
3. Django backend receives via Pusher websocket subscription
   (subscribed to: private-teacher-{account_id})
     ↓
4. Backend decodes proto event, extracts:
   - question text, student answer, correct answer
   - is_correct, error_type (from our question metadata)
     ↓
5. Backend publishes to Custom LLM Server:
   POST {CUSTOM_LLM_URL}/update-quiz-results
   Body: { channel, results: [{ question, answer, is_correct, error_type }] }
     ↓
6. Custom LLM Server stores quiz results for this channel
     ↓
7. Next time student speaks to the avatar:
   - ConvoAI sends POST /chat/completions to Custom LLM
   - Custom LLM enriches system prompt with quiz results
   - LLM generates response that references quiz performance
     ↓
8. Avatar: "I noticed you picked 'the' instead of 'a' for 'university'.
   In English, we use 'a' before consonant sounds. Can you think of
   other words where you'd use 'a' vs 'the'?"
```

---

## 7. Environment Variables

```bash
# Same credentials as ConvoAI (from Agora Console)
AGORA_APP_ID=your_app_id
AGORA_APP_CERTIFICATE=your_app_certificate

# Frontend
VITE_AGORA_APP_ID=your_app_id  # Same value, exposed to Vite
```

### NPM packages

```bash
# Frontend
npm install agora-rtc-sdk-ng    # RTC for audio

# Backend
pip install agora-token          # Token generation
```

---

## References

- [RTC Web SDK](https://docs.agora.io/en/video-calling/overview/product-overview)
- [RTM/Signaling](https://docs.agora.io/en/signaling/overview/product-overview)
- [Token generation](https://docs.agora.io/en/video-calling/develop/authentication-workflow)
