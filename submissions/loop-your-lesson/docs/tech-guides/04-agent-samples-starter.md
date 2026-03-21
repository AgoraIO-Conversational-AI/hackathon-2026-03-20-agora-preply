# agent-samples Starter Repo — Technology Guide

Map of the official Agora ConvoAI starter. What to copy, adapt, or ignore.

---

## 1. Overview

**Repo:** https://github.com/AgoraIO-Conversational-AI/agent-samples
**License:** MIT

Full-stack voice and video AI agent with Python backend and React frontends.
We adapt pieces into our Django + React stack rather than forking the whole repo.

---

## 2. Repository Structure

```
agent-samples/
├── AGENT.md                          # AI assistant implementation guide
├── CLAUDE.md                         # Claude Code instructions
├── ecosystem.config.js               # PM2 production config
├── simple-backend/                   # Python Flask backend
│   ├── .env.example                  # Full config template
│   ├── local_server.py              # Flask entry point (3 routes)
│   ├── core/
│   │   ├── agent.py                 # Payload building + API calls
│   │   ├── config.py                # Profile-based env var system
│   │   ├── tokens.py                # v007 token generation (RTC+RTM)
│   │   └── utils.py                 # Channel name generation
│   ├── requirements-local.txt       # flask + python-dotenv
│   └── requirements.txt             # No external deps (stdlib only)
├── react-voice-client/               # Next.js voice-only client
├── react-video-client-avatar/        # Next.js voice + Anam avatar client
├── simple-voice-client-no-backend/   # Standalone HTML/JS (demo only)
├── simple-voice-client-with-backend/ # Full-stack JS client
├── recipes/
│   └── thymia.md                    # Thymia voice biomarker integration
└── design/                           # UI assets
```

---

## 3. Backend (simple-backend/)

### Flask server (`local_server.py`)

Three endpoints:

```
GET /start-agent?channel=test&profile=VOICE&pipeline_id=xxx&connect=false&debug
GET /hangup-agent?agent_id=xxx
GET /health
```

### Profile system (`core/config.py`)

All env vars use `<PROFILE>_<VARIABLE>` naming:
```bash
VOICE_APP_ID=your_app_id
VOICE_APP_CERTIFICATE=your_cert
VOICE_LLM_API_KEY=sk-xxx
VOICE_LLM_MODEL=gpt-4o-mini
VOICE_TTS_VENDOR=rime
VOICE_TTS_KEY=your_key
VOICE_TTS_VOICE_ID=astra
VOICE_ASR_VENDOR=ares
VOICE_ASR_LANGUAGE=en-US
VOICE_ENABLE_AIVAD=true
```

For video avatar profile:
```bash
VIDEO_APP_ID=your_app_id
VIDEO_APP_CERTIFICATE=your_cert
VIDEO_AVATAR_VENDOR=anam
VIDEO_AVATAR_API_KEY=your_anam_key
VIDEO_AVATAR_ID=your_avatar_id
VIDEO_TTS_VENDOR=elevenlabs
VIDEO_TTS_KEY=your_key
```

### Fixed UIDs
- Agent: 100
- User: 101
- Agent video: 102
- Token expiry: 24 hours

### Payload builder (`core/agent.py`)

Builds the complete JSON payload for the ConvoAI REST API.

Key behaviors:
- **Pipeline mode:** Just sends `pipeline_id` — Agora resolves all config
- **Inline mode:** Full control over ASR, TTS, LLM, avatar
- **Custom LLM:** When `LLM_VENDOR=custom`, passes channel/app_id/tokens through `llm_config.params`
- **After agent creation:** Non-blocking POST to custom LLM's `/register-agent`

### Token generation (`core/tokens.py`)

Uses v007 token format with RTC + RTM services.
Generates tokens with join channel, publish audio/video/data, and RTM login privileges.

---

## 4. Frontend — Voice Client (react-voice-client/)

Next.js app with Agora RTC SDK integration.

Key patterns to port to our React app:
- `AgoraProvider` — wraps app with RTC client context
- `useAgora` hook — handles join/leave/publish/subscribe
- Audio track management — local mic → remote agent audio

### Minimal React hook pattern

```typescript
// What we need to port to frontend/src/views/VoicePractice/
import AgoraRTC from "agora-rtc-sdk-ng";

const client = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });

async function joinChannel(appId: string, channel: string, token: string, uid: number) {
  await client.join(appId, channel, token, uid);
  const localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack();
  await client.publish([localAudioTrack]);

  client.on("user-published", async (user, mediaType) => {
    await client.subscribe(user, mediaType);
    if (mediaType === "audio") {
      user.audioTrack?.play(); // Play agent's voice
    }
  });
}
```

---

## 5. Frontend — Avatar Client (react-video-client-avatar/)

Extends the voice client with Anam avatar rendering.
The avatar receives the agent's TTS audio and renders lip-synced video.

Key addition over voice client:
- Anam SDK initialization
- Video element for avatar rendering
- Avatar persona configuration

---

## 6. What We Take vs What We Build

| Component | From agent-samples | Our implementation |
|-----------|-------------------|-------------------|
| Token generation | `core/tokens.py` | Port to `backend/services/agora/tokens.py` |
| Agent start/stop | `core/agent.py` | Rewrite as `backend/services/convoai/client.py` (async, Django settings) |
| Profile config | `core/config.py` | Replace with Django settings + .env |
| RTC join flow | `react-voice-client/` | Port hook to `frontend/src/views/VoicePractice/` |
| Anam avatar | `react-video-client-avatar/` | Port to our VoicePractice view |
| Custom LLM | Reference only | Build our own with lesson context injection |
| Thymia recipe | `recipes/thymia.md` | Follow recipe, adapt for our stack |

### What to ignore
- `simple-voice-client-no-backend/` — HTML demo, not useful
- `simple-voice-client-with-backend/` — JS backend, we use Django
- `ecosystem.config.js` — PM2 config, we use mprocs
- Pipeline mode — we use Custom LLM mode

---

## 7. Quick Reference

```bash
# Clone for reference (don't fork)
git clone https://github.com/AgoraIO-Conversational-AI/agent-samples.git /tmp/agent-samples

# Run the starter backend (for testing)
cd /tmp/agent-samples/simple-backend
cp .env.example .env
# Fill in your Agora + LLM + TTS credentials
pip install -r requirements-local.txt
python local_server.py
# Server at http://localhost:8080

# Start an agent
curl "http://localhost:8080/start-agent?channel=test&profile=VOICE"
```

---

## References

- [agent-samples repo](https://github.com/AgoraIO-Conversational-AI/agent-samples)
- [AGENT.md](https://github.com/AgoraIO-Conversational-AI/agent-samples/blob/main/AGENT.md)
