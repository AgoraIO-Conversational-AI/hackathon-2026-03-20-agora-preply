# Integration Patterns — How Everything Connects

This document ties all technologies together for our specific project.
Read after the individual tech guides (01-06).

---

## 1. The Full Voice Practice Flow

```
Student clicks "Start Practice" in our app
    │
    ├── 1. Frontend calls: POST /api/voice-practice/start/
    │      Body: { lesson_id, student_id }
    │
    ├── 2. Django backend:
    │      a. Fetch lesson data (errors, themes, level) from SkillExecution
    │      b. Build ConvoAI agent config (Contract 5)
    │      c. Generate RTC tokens (student + agent)
    │      d. Build system prompt from lesson errors
    │      e. Start ConvoAI agent: POST .../join
    │         - Custom LLM URL points to our middleware
    │         - System prompt includes student's actual mistakes
    │         - Greeting: "Hi Maria! Let's practice articles today."
    │      f. (Optional) Create Anam session for avatar
    │      g. Return to frontend: { channel, token, agent_id, anam_token? }
    │
    ├── 3. Frontend:
    │      a. Join RTC channel with student token (useAgora hook)
    │      b. (Optional) Initialize Anam avatar with session token
    │      c. Student's mic audio streams to ConvoAI agent
    │
    ├── 4. Conversation loop (in Agora cloud):
    │      a. Student speaks → ASR transcribes
    │      b. ConvoAI sends to Custom LLM: POST /chat/completions
    │      c. Custom LLM enriches with lesson context + quiz results
    │      d. Forwards to OpenAI → streams response back
    │      e. ConvoAI runs TTS → audio streams to student
    │      f. (Optional) Anam renders lip-synced avatar
    │
    ├── 5. Quiz result adaptation (the key innovation):
    │      a. Student answers Classtime quiz in parallel
    │      b. Classtime fires Pusher event: student_response
    │      c. Django backend receives, decodes result
    │      d. Backend updates Custom LLM: POST /update-quiz-results
    │         OR updates ConvoAI agent: POST .../update (system_messages)
    │      e. Next conversation turn references quiz performance
    │
    └── 6. Session ends:
          a. Student clicks "End Practice" OR idle timeout
          b. Frontend leaves RTC channel
          c. Backend stops agent: POST .../leave
          d. Backend saves practice session data
          e. Data available for teacher's morning briefing
```

---

## 2. Backend Service Layer

```
backend/services/
├── convoai/
│   └── client.py          # ConvoAIClient: start/stop/update/speak agents
│                          # See: 01-agora-convoai.md § 7
│
├── agora/
│   └── tokens.py          # generate_rtc_token(), generate_rtm_token()
│                          # See: 02-agora-rtc-rtm.md § 4
│
├── anam/
│   └── client.py          # create_anam_session() → session token
│                          # See: 05-anam-avatars.md § 2
│
├── classtime/
│   ├── client.py          # REST + Proto API client
│   ├── sessions.py        # create_practice_session(), get_results()
│   ├── questions.py       # create_question_set(), create_question()
│   ├── schemas.py         # Question payloads, DraftJS helpers
│   └── realtime.py        # Pusher subscription → quiz result events
│                          # See: docs/classtime-api-guide.md
│
└── custom_llm/
    └── context.py         # build_agent_system_prompt() from Contract 5
                           # See: 03-custom-llm-server.md § 5
```

---

## 3. Frontend Component Map

```
frontend/src/views/VoicePractice/
├── VoicePractice.tsx      # Main view: start/stop, layout
├── useAgora.ts            # RTC hook: join/leave/audio
│                          # See: 02-agora-rtc-rtm.md § 2
├── AnamAvatar.tsx         # Video avatar component
│                          # See: 05-anam-avatars.md § 2
├── PracticeControls.tsx   # Start/end buttons, status display
└── PracticeStatus.tsx     # Connection status, quiz sync indicator
```

---

## 4. Contract 5: ConvoAI Agent Config

From `docs/development-plan.md` — this is what the backend builds
before starting the ConvoAI agent:

```python
ConvoAIAgentConfig = {
    "student_id": "student_123",
    "student_name": "Maria",
    "student_level": "B1",
    "lesson_errors": [
        {
            "type": "article_confusion",
            "severity": "moderate",
            "original": "I went to the university",
            "corrected": "I went to a university",
            "explanation": "Use 'a' for first mention of non-specific nouns"
        },
        {
            "type": "irregular_past_tense",
            "severity": "minor",
            "original": "I goed to the store",
            "corrected": "I went to the store",
            "explanation": "'go' has irregular past tense 'went'"
        }
    ],
    "lesson_themes": [
        {"topic": "daily routines", "vocabulary": ["commute", "schedule", "habit"]},
        {"topic": "shopping", "vocabulary": ["groceries", "checkout", "receipt"]}
    ],
    "classtime_session_code": "ABC123",
    "language_pair": {"l1": "Spanish", "l2": "English"}
}
```

---

## 5. Environment Variable Checklist

All env vars needed for the full voice practice stack:

```bash
# === Agora (Required) ===
AGORA_APP_ID=                     # From Agora Console
AGORA_APP_CERTIFICATE=            # From Agora Console
AGORA_CUSTOMER_ID=                # From Agora Console > RESTful API
AGORA_CUSTOMER_SECRET=            # From Agora Console > RESTful API

# === TTS (Required) ===
TTS_VENDOR=rime                   # rime, elevenlabs, microsoft, etc.
TTS_KEY=                          # TTS provider API key
TTS_VOICE_ID=astra               # Voice ID from provider

# === Custom LLM Server (Required) ===
CUSTOM_LLM_URL=                   # URL of our Custom LLM middleware
LLM_API_KEY=                      # OpenAI API key (on Custom LLM server)
LLM_MODEL=gpt-4o-mini            # LLM model to use

# === Anam Avatar (Optional) ===
ANAM_API_KEY=                     # From Anam dashboard
VIDEO_AVATAR_ID=                  # Avatar persona ID

# === Thymia (Stretch) ===
THYMIA_API_KEY=                   # From Thymia
THYMIA_ENABLED=false              # Enable on Custom LLM server

# === Django Backend ===
BACKEND_URL=http://localhost:8005
BACKEND_API_TOKEN=                # DRF Token for Custom LLM → Backend calls

# === Frontend ===
VITE_AGORA_APP_ID=                # Same as AGORA_APP_ID, exposed to Vite
VITE_BACKEND_URL=http://localhost:8005
```

---

## 6. Quick Start: Voice Practice from Zero

### Prerequisites
- Agora account with ConvoAI enabled ([console.agora.io](https://console.agora.io))
- OpenAI API key
- TTS provider API key (Rime recommended)

### Steps

```bash
# 1. Clone the Custom LLM Server
git clone https://github.com/AgoraIO-Conversational-AI/server-custom-llm.git
cd server-custom-llm/python
pip install -r requirements.txt

# 2. Configure
export LLM_API_KEY=sk-your-openai-key
export LLM_MODEL=gpt-4o-mini

# 3. Start Custom LLM Server
python -m uvicorn custom_llm:app --host 0.0.0.0 --port 8100

# 4. Expose to internet (for Agora cloud to reach)
cloudflared tunnel --url http://localhost:8100
# Note the URL: https://xxx-yyy.trycloudflare.com

# 5. Set the Custom LLM URL in your Django .env
echo "CUSTOM_LLM_URL=https://xxx-yyy.trycloudflare.com/chat/completions" >> .env

# 6. Start Django backend (handles token gen + agent lifecycle)
cd backend && uv run manage.py runserver 0.0.0.0:8005

# 7. Start frontend
cd frontend && bun dev

# 8. Open browser → Start Practice → speak to the avatar
```

---

## 7. Demo Happy Path

For the judges, this is the voice practice segment:

1. **Setup**: Maria just completed a Classtime quiz (6/8, struggled with articles)
2. **Start**: Maria clicks "Start Voice Practice"
3. **Greeting**: Avatar says "Hi Maria! Great job on the quiz — let's work on those articles."
4. **Conversation**: Avatar steers toward article usage in context
5. **Adaptation**: If Maria uses wrong article, avatar corrects gently with explanation
6. **Quiz sync**: (If live) new quiz result comes in → avatar pivots topic
7. **Wrap up**: After 3-5 minutes, avatar summarizes what was practiced
8. **Result**: Session data saved → appears in teacher's morning briefing

---

## References

- [01-agora-convoai.md](01-agora-convoai.md) — ConvoAI API
- [02-agora-rtc-rtm.md](02-agora-rtc-rtm.md) — Transport layers
- [03-custom-llm-server.md](03-custom-llm-server.md) — Middleware
- [04-agent-samples-starter.md](04-agent-samples-starter.md) — Starter repo
- [05-anam-avatars.md](05-anam-avatars.md) — Video avatars
- [06-thymia-biomarkers.md](06-thymia-biomarkers.md) — Voice biomarkers
- [docs/classtime-api-guide.md](../classtime-api-guide.md) — Assessment platform
- [docs/development-plan.md](../development-plan.md) — Contracts and phases
