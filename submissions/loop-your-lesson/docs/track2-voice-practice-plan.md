# Track 2: Voice Practice — Implementation Plan

## Context

**Why**: Track 2 delivers the voice practice layer for the Preply x Agora Hackathon (March 20-21, 2026). When a student presses "Start Session", an Agora ConvoAI agent joins a room with an Anam video avatar. The avatar knows the student's lesson errors, themes, and level. As the student takes a Classtime quiz in parallel, quiz results feed the avatar in real-time via Pusher websockets, adapting the conversation.

**Owner**: Andrew (Track 2)
**Dependency**: Track 1 (Vasyl) provides Django backend, AI skills, Classtime integration.

---

## Architecture Decisions (finalized)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM integration | **Native OpenAI (all sponsors)** | Start with `llm.style: "openai"` (ConvoAI default) + `/update` + `/speak`. Uses gpt-4o-mini. All hackathon sponsors: Agora + OpenAI + Anam + Thymia. Max from OpenAI is a judge. No streaming format conversion needed. Switch to custom proxy later if needed (one config change). |
| Quiz events | **Pusher websockets** | Real-time (<1s). Protobuf decoder documented in classtime-api-guide. More impressive for judges. |
| Django structure | **Services-only** | Build `services/convoai/` and `services/agora/`. Plug into Track 1's Django app later. Avoids merge conflicts. |
| Context injection | **`/update` endpoint** | Refresh `system_messages` on quiz events and periodically to combat context rot. Equivalent to custom proxy for our use case. |
| Instant reactions | **`/speak` with APPEND priority** | Queue quiz reactions after current speech. No jarring interruptions during conversation. |
| Voice biomarkers | **Thymia Sentinel SDK** | Real-time streaming via `thymia-sentinel` package + `student_monitor` policy. Returns actionable tutor recommendations (slow_down, take_break, check_understanding). `go-audio-subscriber` sidecar captures RTC audio, streams to Sentinel WebSocket. Scores + recommendations injected via `/update`. Required for Technology Use score. |
| Interaction model | **Full-duplex concurrent** | Quiz answering and voice practice happen simultaneously. ConvoAI handles full-duplex audio. Student can speak while avatar is speaking. `interruptable: true`. |

---

## ConvoAI API Reference (verified)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v2/projects/{appid}/join` | POST | Start agent (channel, LLM config, TTS, system prompt) |
| `/agents/{agentId}/update` | POST | **Update running agent** — can patch `system_messages`, model, params |
| `/agents/{agentId}/speak` | POST | **Broadcast TTS directly** — bypasses LLM, instant reaction (max 512 bytes) |
| `/agents/{agentId}/leave` | POST | Stop agent |
| `/agents/{agentId}/interrupt` | POST | Stop agent speech (empty body) |
| `/agents/{agentId}` | GET | Query agent status |
| `/agents/{agentId}/history` | GET | Conversation history |

**Auth**: `Authorization: Basic {base64(AGORA_CUSTOMER_ID:AGORA_CUSTOMER_SECRET)}`

**Claude support**: Native via `llm.style: "anthropic"` — but we use custom LLM proxy instead.

**Custom LLM**: Set `llm.url` to our server. Must implement OpenAI Chat Completions SSE streaming format. Request includes `messages` + optional `context.presence` (if RTM enabled).

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Frontend (React/Vite)                         │
│                                                                  │
│  ┌──────────────────┐          ┌───────────────────────────────┐ │
│  │ Classtime Quiz   │          │ Voice Practice Component      │ │
│  │ (iframe)         │          │                               │ │
│  │                  │          │  ┌─────────────────────────┐  │ │
│  │  Student answers │◄─────────│──│    Anam Avatar          │  │ │
│  │  questions while │ both     │  │    (video + lip sync)   │  │ │
│  │  avatar talks    │ active   │  └─────────────────────────┘  │ │
│  │                  │ at once  │  🎤 Agora RTC (full-duplex)   │ │
│  │                  │          │  📷 Webcam capture (5-10s)    │ │
│  └──────────────────┘          │  [End Session]                │ │
│                                └───────────────────────────────┘ │
└────────────┬────────────────────────┬──────────┬─────────────────┘
             │                        │          │
             │ (quiz events)          │ (audio)  │ (webcam frames)
             │                        │          │
┌────────────▼────────────────────────┼──────────▼─────────────────┐
│                    Django Backend   │                             │
│                                    │                             │
│  ┌──────────────────────────────┐  │  ┌───────────────────────┐  │
│  │ POST /api/v1/voice-sessions/ │  │  │ POST .../frame/       │  │
│  │  1. Fetch skill results      │  │  │  Receive webcam JPEG  │  │
│  │  2. Build system prompt      │  │  │  → Claude Vision API  │  │
│  │  3. Generate Agora RTC token │  │  │  → "confused look"    │  │
│  │  4. Start ConvoAI agent      │  │  │  → "low confidence"   │  │
│  │     (native Claude)          │  │  │  → update Redis       │  │
│  │  5. Start Pusher listener    │  │  │  → POST /update       │  │
│  │  6. Store context in Redis   │  │  └───────────────────────┘  │
│  │  7. Return {channel, token}  │  │                             │
│  └──────────────────────────────┘  │                             │
│                                    │                             │
│  ┌──────────────────────────────┐  │                             │
│  │ Pusher Listener (background) │  │                             │
│  │  On binary-answer-added:     │  │                             │
│  │    1. Decode protobuf        │  │                             │
│  │    2. Enrich with details    │  │                             │
│  │    3. Map → source error     │  │                             │
│  │    4. Update Redis mastery   │  │                             │
│  │    5. /speak (APPEND)        │  │                             │
│  │    6. /update (new prompt)   │  │                             │
│  └──────────────────────────────┘  │                             │
└──────────┬──────────────────┬──────┼─────────────────────────────┘
           │                  │      │
┌──────────▼──────────┐  ┌───▼──────▼──────────────┐
│  Agora ConvoAI      │  │  Classtime API           │
│                     │  │                          │
│  STT → Claude → TTS │  │  Pusher websockets       │
│  (native, style:    │  │  (binary-answer-added)   │
│   "anthropic")      │  │                          │
│                     │  │  getSessionDetails       │
│  Full-duplex RTC    │  │  getAnswers              │
│  interruptable:true │  │                          │
└─────────────────────┘  └──────────────────────────┘
```

---

## Data Flow: Concurrent Quiz + Voice Practice

Student does both at the same time — answering quiz questions while talking to avatar.
ConvoAI is full-duplex: student can speak while avatar is speaking.

```
TIME →

Student:  [answering Q1]  [speaking to avatar]  [answering Q2]  [speaking]
              │                                      │
Pusher:       │ Q1: WRONG (articles)                 │ Q2: CORRECT (past tense)
              ▼                                      ▼
Backend:   decode + enrich                        decode + enrich
           update Redis mastery                   update Redis mastery
              │                                      │
              ├─ /speak (APPEND):                     ├─ /speak (APPEND):
              │  "Articles are tricky!                │  "Nice work on past
              │   Let's practice."                    │   tense!"
              │  (queued after current speech)        │
              │                                      │
              └─ /update: system_messages             └─ /update: system_messages
                 refreshed with mastery state            refreshed with mastery state
                 (ready for next LLM call)               (past tense → de-prioritized)

Avatar:  [having conversation]  [says quiz reaction]  [continues conversation]
         "Tell me about your     "Articles are tricky   "So you went to school—
          morning routine"        Let's practice."       do you go to THE park
                                                         or just 'park'?"
```

### Quiz Event Processing Detail

```
Student answers Q1 (articles): WRONG — wrote "the school"
  │
  ▼
Pusher: binary-answer-added on private-teacher-session-{CODE}
  │
  ▼
Backend Pusher listener:
  1. Decode protobuf → {question_id: "q-1", correctness: "WRONG"}
  2. getSessionDetails → {title: "Articles", derivedFrom: "7fdd-..."}
  3. getAnswers → {answerGap: {gaps: [{content: "the school"}]}}
  4. Map derivedFrom → questions_data → source_ref:
     {error_type: "grammar", subtype: "articles",
      original: "I go to the school", corrected: "I go to school"}
  │
  ▼
  5. Update Redis mastery state:
     voice:{session_id}:mastery → articles: {status: "struggling", quiz: "WRONG"}
  │
  ├──→ POST /agents/{id}/speak  (priority: APPEND)
  │    "I noticed you just worked on articles in the quiz —
  │     those can be tricky! Let's practice them together."
  │    (Queued after current speech, no interruption)
  │
  └──→ POST /agents/{id}/update
       system_messages: [refreshed prompt with mastery state]
       (Next LLM call uses updated context)
```

### Thymia Voice Biomarker Flow

```
ConvoAI Agent (Agora cloud) ← student's RTC audio stream
  │
  ▼
go-audio-subscriber (sidecar process)
  │  Joins RTC channel as subscriber
  │  Captures student's audio chunks (10s+ segments)
  │  Sends to Thymia Sentinel API
  ▼
Thymia API → returns biomarker scores:
  {stress: 0.72, exhaustion: 0.55, distress: 0.65}
  │
  ▼
Backend:
  1. Receive scores from go-audio-subscriber callback
  2. Update Redis mastery state:
     voice:{session_id}:biomarkers → {stress: 0.72, exhaustion: 0.55}
  3. POST /agents/{id}/update
     system_messages now include:
     "## Voice Biomarkers (real-time)
      - Student shows high stress (0.72). Speak slowly, use shorter
        sentences, offer encouragement before corrections.
      - Student shows moderate fatigue (0.55). Consider easier topics."
  │
  ▼
Next avatar response adapts tone and pacing
```

**Thymia pedagogical mapping:**

| Signal | Threshold | Avatar behavior |
|--------|-----------|----------------|
| Stress > 0.7 | High | Slow down, shorter sentences, more encouragement |
| Exhaustion > 0.6 | Moderate | Suggest break, switch to easier topic |
| Low self-esteem > 0.5 | Moderate | Extra positive reinforcement |
| Happy > 0.6 | Engaged | Increase difficulty, new challenges |

---

## Mastery State (Redis)

```python
# Key: voice:{session_id}:mastery
# TTL: 2 hours
{
    "errors": [
        {
            "error_type": "grammar",
            "subtype": "articles",
            "original": "I go to the school",
            "corrected": "I go to school",
            "quiz_result": "WRONG",         # null | CORRECT | WRONG
            "quiz_answer": "the school",    # what student wrote
            "focus_level": "critical",       # low | medium | high | critical
            "voice_practiced": false,        # has avatar covered this?
        },
        {
            "error_type": "grammar",
            "subtype": "past_tense_irregular",
            "original": "I goed to cinema",
            "corrected": "I went to the cinema",
            "quiz_result": "CORRECT",
            "quiz_answer": "went",
            "focus_level": "low",            # mastered → de-prioritize
            "voice_practiced": true,
        },
        # ... more errors
    ],
    "summary": {
        "tested": 2,
        "correct": 1,
        "wrong": 1,
        "untested": 2,
        "current_focus": ["articles", "3rd_person"],
    },
    "quiz_events": [
        # Raw quiz events for audit trail
        {"question_id": "q-1", "correctness": "WRONG", "timestamp": "..."},
    ],
    "biomarkers": {
        # From Thymia voice analysis (updated every 10-15s)
        "stress": 0.72,             # 0.0-1.0
        "exhaustion": 0.55,         # 0.0-1.0
        "distress": 0.65,           # 0.0-1.0
        "updated_at": "...",
    },
}
```

---

## LLM Strategy: Native First, Proxy Later

### Phase 1: Native OpenAI (all sponsors aligned)

ConvoAI calls OpenAI directly via `llm.style: "openai"` (default). Context injection via `/update`:

```python
# Agent start config
{
    "llm": {
        "url": "https://api.openai.com/v1/chat/completions",
        "api_key": OPENAI_API_KEY,
        "style": "openai",
        "system_messages": [{"role": "system", "content": initial_prompt}],
        "params": {"model": "gpt-4o-mini", "max_tokens": 256}
    },
    "advanced_features": {
        "turn_detection": {"silence_duration_ms": 500}
    }
}
```

Context stays fresh via `/update` — called on every quiz event and video frame analysis. The `/update` completes in ~100ms, well before the student's next utterance (5-10s between turns).

### Phase 2 (stretch): Custom LLM Proxy

If we need per-turn conversation-history-aware context (e.g., "student has misused articles 3 times in voice practice, not just in quiz"), switch by changing one config:

```python
# Just change llm.url — everything else stays the same
"llm": {
    "url": "https://our-backend/api/v1/convoai-llm/",
    "api_key": "",
    "system_messages": [{"role": "system", "content": initial_prompt}],
    "params": {"model": "claude-sonnet-4-20250514", "max_tokens": 256}
}
```

The proxy must implement OpenAI Chat Completions SSE format. See `docs/tech-guides/03-custom-llm-server.md` for the full request/response spec. Zero wasted work — all services, context builder, and mastery state work identically in both modes.

---

## Implementation Plan

### Step 1: Agora Service Layer (no Track 1 dependency)

**Files:**
- `backend/services/agora/__init__.py`
- `backend/services/agora/tokens.py` — RTC token generation
- `backend/services/convoai/__init__.py`
- `backend/services/convoai/client.py` — ConvoAI REST API client
- `backend/services/convoai/schemas.py` — Pydantic request/response models

**ConvoAI client methods:**
```python
class ConvoAIClient:
    def start_agent(self, config: AgentStartConfig) -> AgentResponse
    def stop_agent(self, agent_id: str) -> None
    def update_agent(self, agent_id: str, system_messages: list[dict]) -> None
    def speak(self, agent_id: str, text: str) -> None
    def interrupt(self, agent_id: str) -> None
    def get_agent_status(self, agent_id: str) -> AgentStatus
    def get_history(self, agent_id: str) -> list[dict]
```

**AgentStartConfig** (maps to `/join` request body):
```python
class AgentStartConfig(BaseModel):
    channel_name: str
    agent_rtc_uid: int = 1000
    system_prompt: str
    llm_url: str            # Our custom LLM proxy URL
    llm_api_key: str = ""   # Not needed (we handle auth)
    llm_model: str = "claude-sonnet-4-20250514"
    tts_vendor: str = "rime"
    tts_voice: str = "astra"
    tts_language: str = "en"
    stt_language: str = "en"
    enable_rtm: bool = False  # We use /update + /speak instead
```

### Step 2: Context Builder

**Files:**
- `backend/services/convoai/context.py` — 4-layer context builder for voice practice

Adapts the pattern from `docs/deep-dives/05-context-injection.md`:

```python
class VoicePracticeContext:
    """Build and maintain system prompt for voice practice agent."""

    def __init__(
        self,
        student_name: str,
        student_level: str,
        language_pair: LanguagePair,
        errors: list[ErrorOutput],
        themes: list[ThemeOutput],
        conversation_plan: ConversationPlan | None = None,
    ): ...

    def build_initial_prompt(self) -> str:
        """Full system prompt for agent start. All 4 layers."""

    def build_enriched_prompt(self, mastery: MasteryState) -> str:
        """System prompt with live quiz results and mastery state.
        Called on every custom LLM proxy request."""

    def format_quiz_update_speak(self, result: QuizResult) -> str:
        """Short text for /speak endpoint. Max 512 bytes."""
```

**System prompt structure:**
```
## Role
You are {student_name}'s English speaking practice partner.
You are warm, patient, and encouraging.

## Student Profile
- Name: {student_name}
- Level: {level} (CEFR)
- Native language: {l1}
- Learning: {l2}

## Lesson Errors (from today's lesson)
1. [CRITICAL] Articles: said "I go to the school" → should be "I go to school"
2. [LOW] Past tense: said "I goed" → should be "I went" (MASTERED in quiz)
3. [CRITICAL] 3rd person: said "She don't like" → should be "She doesn't like"
...

## Lesson Themes
- Morning routine (vocabulary: wake up, commute, breakfast)
- Travel planning

## QUIZ RESULTS (live — updated as student answers)
- Q1 (articles): WRONG — student wrote "the school"
  → INCREASE focus on articles
- Q2 (past tense): CORRECT
  → Student has mastered this, reduce focus

## Current Priority
Focus on: articles, 3rd person singular
De-prioritize: past tense (mastered)

## Student State (live — from video + voice analysis)
- Visual: confused, low confidence (updated 5s ago)
- Adaptation: use shorter sentences, more encouragement, scaffold more

## Conversation Instructions
- Have a natural conversation about {theme}
- Weave error practice into the topic naturally
- When student makes an error you know about, use RECAST:
  repeat what they said correctly without lecturing
- Create scenarios that require the focus error patterns
- Keep responses concise (2-3 sentences) — this is spoken conversation
- Don't list errors or quiz results to the student
- If student looks confused or frustrated, slow down and encourage
- Student is answering a quiz at the same time — don't interrupt their focus,
  but naturally reference quiz topics when they come up
```

### Step 3: Thymia Voice Biomarker Integration

**Files:**
- `backend/services/convoai/thymia.py` — Thymia API client + biomarker context builder

Thymia is a separate voice analysis service. Architecture:
1. `go-audio-subscriber` (from Agora agent-samples repo) joins the RTC channel
2. It captures student audio and sends to Thymia Sentinel API
3. Thymia returns biomarker scores (stress, exhaustion, emotion)
4. Our backend receives scores and injects into agent context via `/update`

```python
class ThymiaClient:
    """Thymia Sentinel API client for voice biomarkers."""

    BASE_URL = "https://api.thymia.ai"  # Check actual URL from API portal

    def __init__(self, api_key: str) -> None:
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    async def start_analysis(self, student_id: str) -> tuple[str, str]:
        """Start a mental wellness model run. Returns (run_id, upload_url)."""
        resp = await httpx.AsyncClient().post(
            f"{self.BASE_URL}/v1/models/mental-wellness",
            headers=self.headers,
            json={
                "user": {"userLabel": student_id},
                "language": "en-GB",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["id"], data["recordingUploadUrl"]

    async def get_results(self, run_id: str) -> dict | None:
        """Poll for biomarker results. Returns None if not ready."""
        resp = await httpx.AsyncClient().get(
            f"{self.BASE_URL}/v1/models/mental-wellness/{run_id}",
            headers=self.headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] == "COMPLETE_OK":
            return data["results"]
        return None


def build_thymia_context(biomarkers: dict) -> str:
    """Build context block from Thymia biomarker scores."""
    stress = biomarkers.get("stress", {}).get("value", 0)
    exhaustion = biomarkers.get("exhaustion", {}).get("value", 0)

    instructions = []
    if stress > 0.7:
        instructions.append(
            f"Student shows high stress ({stress:.1f}). Speak slowly, use shorter "
            "sentences, offer encouragement before corrections."
        )
    if exhaustion > 0.6:
        instructions.append(
            f"Student shows fatigue ({exhaustion:.1f}). Consider wrapping up or "
            "switching to easier topics."
        )
    if not instructions:
        instructions.append("Student seems comfortable. Maintain current pace.")

    return "## Voice Biomarkers (real-time)\n" + "\n".join(f"- {i}" for i in instructions)
```

**Note:** The `go-audio-subscriber` sidecar is a pre-built Go binary from the Agora agent-samples repo. See `docs/tech-guides/06-thymia-biomarkers.md` for setup.

### Step 4: Pusher Quiz Bridge

**Files:**
- `backend/services/convoai/quiz_bridge.py` — Real-time quiz event processing

```python
class QuizBridge:
    """Connect Classtime Pusher events to ConvoAI agent context."""

    def __init__(self, session_id: str, session_code: str,
                 agent_id: str, questions_data: dict):
        self.convoai = ConvoAIClient()
        self.pusher = None  # pysher client

    async def start(self):
        """Subscribe to Pusher channel, start processing events."""
        # 1. Get Pusher config: proto_call("Session", "getPusherConfig", ...)
        # 2. Connect to Pusher with api_key + cluster
        # 3. Auth: proto_call("Session", "getRealtimeAuthentication", ...)
        # 4. Subscribe to private-teacher-session-{CODE}
        # 5. Bind binary-answer-added → self._on_answer

    async def _on_answer(self, data: str):
        """Process quiz answer event."""
        # 1. Decode protobuf (reuse decoder from classtime-api-guide.md §10)
        decoded = decode_answer_event(data)

        # 2. Enrich with question details
        details = await self._enrich(decoded)

        # 3. Map to source error
        source_ref = self.questions_data[decoded["question_id"]]

        # 4. Update mastery state in Redis
        await self._update_mastery(source_ref, decoded["correctness"], details)

        # 5. Instant reaction via /speak
        speak_text = self.context.format_quiz_update_speak(decoded, source_ref)
        await self.convoai.speak(self.agent_id, speak_text)

        # 6. Refresh system prompt via /update
        mastery = await self._load_mastery()
        new_prompt = self.context.build_enriched_prompt(mastery)
        await self.convoai.update_agent(
            self.agent_id,
            [{"role": "system", "content": new_prompt}]
        )

    async def stop(self):
        """Disconnect Pusher, cleanup."""
```

### Step 5: Frontend — Voice Practice UI (already built, wire to real backend APIs)

**Files (already exist):**
- `frontend/src/views/VoicePractice/VoicePractice.tsx` — Main container
- `frontend/src/views/VoicePractice/AnamAvatar.tsx` — Anam SDK wrapper
- `frontend/src/views/VoicePractice/useVoiceSession.ts` — Session lifecycle hook
- `frontend/src/views/VoicePractice/useAgoraRTC.ts` — Agora RTC connection hook
- `frontend/src/services/voiceApi.ts` — API client

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│            Voice Practice Session                    │
│            Student: Maria · Level: B1                │
├────────────────────────┬────────────────────────────┤
│                        │                            │
│   Classtime Quiz       │    Speaking Practice       │
│   (iframe)             │                            │
│                        │    ┌──────────────────┐    │
│   ┌─────────────────┐  │    │                  │    │
│   │ Q1: Fill in     │  │    │   Anam Avatar    │    │
│   │ the blank...    │  │    │   (video feed)   │    │
│   │                 │  │    │                  │    │
│   │ [___] school    │  │    └──────────────────┘    │
│   └─────────────────┘  │                            │
│                        │    🎤 Listening...          │
│   Progress: 1/4        │    [End Session]            │
│                        │                            │
└────────────────────────┴────────────────────────────┘
```

**Session lifecycle:**
```typescript
// useVoiceSession.ts
function useVoiceSession(studentId: string, lessonId: string) {
  const [session, setSession] = useState<VoiceSession | null>(null)
  const [status, setStatus] = useState<'idle' | 'connecting' | 'active' | 'ended'>('idle')

  const start = async () => {
    setStatus('connecting')
    // POST /api/v1/voice-sessions/
    const data = await voiceApi.startSession(studentId, lessonId)
    setSession(data)
    setStatus('active')
  }

  const stop = async () => {
    if (session) {
      await voiceApi.stopSession(session.id)
      setStatus('ended')
    }
  }

  return { session, status, start, stop }
}
```

### Step 6: Integration & Demo

- Seed demo data: Maria (B1, Spanish→English)
- Seed skill results with 4 errors (articles, past tense, 3rd person, prepositions)
- Seed Classtime session with 4 questions mapping to those errors
- E2E test: start session → avatar greets → answer quiz → avatar adapts
- Polish: avatar persona, TTS voice, conversation naturalness

---

## File Summary

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/services/agora/tokens.py` | RTC token generation |
| 2 | `backend/services/convoai/client.py` | ConvoAI REST API client (start/stop/update/speak) |
| 3 | `backend/services/convoai/schemas.py` | Pydantic models for all request/response types |
| 4 | `backend/services/convoai/context.py` | 4-layer system prompt builder + mastery + visual state |
| 5 | `backend/services/convoai/quiz_bridge.py` | Pusher listener + quiz→mastery→agent pipeline |
| 6 | `backend/services/convoai/thymia.py` | Thymia API client + biomarker context builder |
| 7 | `frontend/src/views/VoicePractice/VoicePractice.tsx` | Main UI (quiz iframe + avatar, concurrent) |
| 8 | `frontend/src/views/VoicePractice/AnamAvatar.tsx` | Anam SDK wrapper component |
| 9 | `frontend/src/views/VoicePractice/useVoiceSession.ts` | Session lifecycle hook |
| 10 | `frontend/src/views/VoicePractice/useAgoraRTC.ts` | Agora RTC connection hook |
| 11 | `frontend/src/services/voiceApi.ts` | API client for voice endpoints |

**Total: 11 files** (6 backend services + 5 frontend)

Stretch: `backend/services/convoai/custom_llm.py` — Custom LLM proxy (add when needed, one config change to activate).

Note: VoiceSession model + Django views/serializers/urls will be added when plugging into Track 1's Django app structure.

---

## Track 1 Status (after Vasyl's push — bec137a)

Vasyl pushed 115 files. Here's what's ready:

### Already Built (use directly)
- **All Django models**: Teacher, Student, Lesson, SkillExecution, ClasstimeSession, TutoringRelationship, Conversation, Message, ToolExecution, DailyBriefing
- **All models use UUID PKs** + TimeStampedModel base
- **API stubs** at `/api/v1/*` — all return 501, ready to implement
- **React frontend**: full chat UI, widgets, design system, routing, TypeScript types
- **Infrastructure**: Docker (PostgreSQL 5432, Redis 6381, Temporal 7233), mprocs, Makefile
- **Dependencies**: anthropic, httpx, redis, temporalio, pydantic (backend); react-query, react-router, tailwind (frontend)

### What Track 2 Adds
| Need | Where |
|------|-------|
| VoiceSession model | `backend/apps/voice_sessions/` |
| ConvoAI service | `backend/services/convoai/` |
| Agora service | `backend/services/agora/` |
| Voice practice API | `backend/config/api_urls.py` |
| Voice practice frontend | `frontend/src/views/VoicePractice/` |
| Agora env vars | `.env.example` |

---

## Build Order (updated for Track 1 codebase)

```
PHASE 1 — Get an agent talking (no proxy needed)
  ├── 1. Add Agora env vars to .env + settings
  ├── 2. backend/services/agora/tokens.py (RTC token gen)
  ├── 3. backend/services/convoai/schemas.py (Pydantic models)
  ├── 4. backend/services/convoai/client.py (ConvoAI API: start/stop/update/speak)
  ├── 5. backend/services/convoai/context.py (initial 4-layer prompt)
  ├── 6. Add voice-sessions endpoints to config/api_urls.py
  ├── 7. Frontend: already built — /voice-practice route, VoicePractice + Agora RTC + Anam
  ├── 8. (done) Wire frontend to real backend APIs
  └── MILESTONE: open browser, see avatar, have basic conversation

PHASE 2 — Make agent context-aware (uses existing models)
  ├── 9. Read SkillExecution outputs from DB (errors, themes, level)
  ├── 10. Enrich context.py with mastery state support
  ├── 11. Redis (already at :6381) for session mastery state
  ├── 12. /update calls to refresh system_messages with mastery
  └── MILESTONE: agent knows student's errors and adapts conversation

PHASE 3 — Real-time quiz feedback loop (THE INNOVATION)
  ├── 13. backend/services/convoai/quiz_bridge.py (Pusher + protobuf)
  ├── 14. Wire /speak (APPEND) + /update into quiz_bridge
  ├── 15. Read ClasstimeSession from DB for session_code + questions_data
  ├── 16. Frontend: quiz iframe + avatar side-by-side (concurrent)
  └── MILESTONE: answer quiz question wrong → avatar adapts immediately

PHASE 4 — Thymia voice biomarkers
  ├── 17. backend/services/convoai/thymia.py (Thymia API client)
  ├── 18. Set up go-audio-subscriber sidecar (from agent-samples repo)
  ├── 19. Inject biomarker scores into mastery → /update
  └── MILESTONE: avatar detects stress, adapts tone and pacing

PHASE 5 — Integration + demo
  ├── 20. VoiceSession Django model (persist results for teacher briefing)
  ├── 21. Seed demo data using existing models
  ├── 22. E2E test with seeded Maria scenario
  └── MILESTONE: demo-ready happy path

STRETCH — Custom LLM proxy (if time permits)
  ├── backend/services/convoai/custom_llm.py
  ├── Change llm.url in agent start config (one line)
  └── BENEFIT: per-turn conversation-history-aware context
```

---

## Verification Plan

### Per-Step Verification
1. **ConvoAI client**: Start agent via API, verify audio works in Agora channel
2. **Context builder**: Given seeded errors, verify system prompt is well-structured
3. **Custom LLM proxy**: Start agent with `llm.url = our proxy`, verify Claude responses stream correctly
4. **Quiz bridge**: Create test Classtime session, answer question, verify Pusher event decoded and mastery updated
5. **Full E2E**: Start session → speak → answer quiz → verify avatar adapts

### Manual Demo Test (the story we tell judges)
1. Maria (B1, Spanish→English) opens voice practice
2. Avatar: "Hi Maria! Let's practice your English today."
3. Maria speaks — avatar hears her errors, gently corrects
4. Maria answers Classtime quiz — gets articles WRONG
5. Avatar: "I noticed articles are tricky! Let's practice those."
6. Avatar steers conversation to use articles naturally
7. Maria answers past tense CORRECT
8. Avatar: "Nice work on past tense!" (moves on to other errors)
9. End session — results available for teacher briefing

---

## Risk Mitigation

| Risk | Mitigation | Fallback |
|------|------------|----------|
| ConvoAI API issues | Test API access early, have mock responses | Pre-recorded demo video |
| Custom LLM proxy SSE format wrong | Test with ConvoAI immediately, match exact OpenAI format | Use native Claude (`style: "anthropic"`) with static prompt |
| Anam avatar not working | Audio-only is still valuable for demo | Skip avatar, focus on voice |
| Pusher protobuf decoding fails | Decoder is documented + tested in classtime-api-guide | Fall back to polling `getAnswersSummary` every 10s |
| Claude responses too long for voice | Set `max_tokens: 256`, add "keep it brief" in prompt | Truncate at sentence boundary |
| Redis unavailable | Use in-memory dict for hackathon | Session-scoped dict in Django |

---

## NOT in scope

- **Full Thymia clinical analysis** — we use Thymia for real-time stress/exhaustion signals; full clinical-grade analysis is post-hackathon
- **Custom LLM proxy** — deferred to stretch. Native Claude + `/update` gives equivalent context freshness. One config change to activate.
- **Conversation persistence** — saving full voice transcripts for review
- **Multi-student sessions** — one student per agent
- **Avatar customization** — fixed avatar for demo
- **Mobile support** — desktop only
- **Production error handling** — basic try/except, not production-grade

---

## What already exists

| Item | In codebase? | Reuse? |
|------|-------------|--------|
| Context injection pattern | `docs/deep-dives/05-context-injection.md` | Adapt 4-layer structure for voice |
| Pusher protobuf decoder | `docs/classtime-api-guide.md` §10 | Copy `decode_answer_event()` + `_decode_fields()` |
| Contract 1 (skill output format) | `docs/development-plan.md` | Use as schema for seeded test data |
| Contract 5 (ConvoAI agent config) | `docs/development-plan.md` | Use as input schema |
| Agora ConvoAI API docs | Researched (see Architecture Decisions) | Full API reference available |
