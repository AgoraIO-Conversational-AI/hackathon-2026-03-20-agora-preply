# Custom LLM Server — Technology Guide

Middleware between Agora ConvoAI and the LLM provider. This is where our
differentiation lives — lesson context injection, quiz result adaptation,
and Thymia biomarker handling.

---

## 1. Overview

### What it does

The Custom LLM Server sits between Agora's ConvoAI engine and the actual LLM
(OpenAI, Anthropic). ConvoAI sends standard OpenAI-compatible chat completion
requests to our server. We intercept, enrich with lesson context, forward to
the LLM, and stream the response back.

### Architecture

```
ConvoAI Agent (Agora cloud)
    │
    │  POST /chat/completions  (OpenAI-compatible)
    │  (includes messages + context: {appId, userId, channel})
    ▼
Custom LLM Server (our FastAPI app)
    │
    │  1. Read context from request params
    │  2. Inject lesson errors, themes, level into system prompt
    │  3. Check for quiz result updates (RTM or DB polling)
    │  4. Forward enriched request to LLM
    │  5. Stream response back (SSE)
    ▼
OpenAI API / Anthropic API
```

### Why we need it

Without the Custom LLM Server, ConvoAI would use a generic system prompt.
With it, we can:
- Ground the conversation in the student's actual lesson errors (Contract 1)
- Inject quiz results mid-conversation (student bombs articles → avatar pivots)
- Process Thymia biomarker signals (student stressed → slow down)
- Add tool calling (look up grammar rules, suggest exercises)

---

## 2. The Starter Repo

**Repo:** https://github.com/AgoraIO-Conversational-AI/server-custom-llm

Three implementations: Python (FastAPI), Node.js (Express), Go (Gin).
We use the **Python implementation**.

### Repository structure

```
server-custom-llm/
├── python/
│   ├── custom_llm.py            # FastAPI server (main file)
│   ├── conversation_store.py    # In-memory conversation storage
│   ├── tools.py                 # Tool definitions + RAG example
│   └── requirements.txt         # openai, uvicorn, fastapi, aiofiles
├── node/                        # Express implementation (has Thymia)
├── go/                          # Gin implementation
├── go-audio-subscriber/         # Go binary for RTC audio capture → Thymia
│   ├── main.go
│   ├── protocol.go
│   └── sdk/                     # Agora native SDK bindings
└── docs/ai/                     # AI-readable documentation
```

---

## 3. API Contract

The Custom LLM Server must expose an **OpenAI Chat Completions-compatible** endpoint.

### Endpoint

```
POST /chat/completions
Content-Type: application/json
```

### Request format

ConvoAI sends this to our server:

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "You are a language practice assistant..."},
    {"role": "user", "content": "I goed to the store yesterday"},
    {"role": "assistant", "content": "I noticed you said 'goed' — the past tense of 'go' is 'went'. Let's practice..."}
  ],
  "tools": [],
  "stream": true,
  "context": {
    "appId": "your_app_id",
    "userId": "agent_100",
    "channel": "lesson_42_practice_student_123",
    "turn_id": "turn_5",
    "timestamp": 1737111452
  }
}
```

The `context` field (added when `vendor=custom`) gives us the channel name
to look up lesson data.

### Response format (SSE streaming)

```
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"role":"assistant"},"index":0}]}
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"Great"},"index":0}]}
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":" job!"},"index":0}]}
data: {"id":"chatcmpl-xxx","choices":[{"delta":{},"finish_reason":"stop","index":0}]}
data: [DONE]
```

### Special: interruption control

Send as first chunk to prevent student from interrupting important corrections:

```json
{"object": "chat.completion.custom_metadata", "metadata": {"interruptable": false}}
```

---

## 4. Python Server Walkthrough

### Core server (`custom_llm.py`)

The server has 3 endpoints:

```python
# Main endpoint — ConvoAI sends all LLM requests here
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # 1. Extract context (appId, channel, userId)
    # 2. Look up conversation history
    # 3. Execute any tool calls (up to 5 passes)
    # 4. Forward to OpenAI with streaming
    # 5. Stream response back to ConvoAI

# RAG endpoint — retrieves context before generating
@app.post("/rag/chat/completions")
async def rag_chat_completions(request: ChatCompletionRequest):
    # Same as above but first retrieves from knowledge base
    # Sends "thinking" filler to user while retrieving

# Audio endpoint — streams pre-recorded audio (not used by us)
@app.post("/audio/chat/completions")
```

### Conversation store (`conversation_store.py`)

In-memory conversation history keyed by `appId:userId:channel`:

```python
# Max 100 messages per conversation
# Auto-trims to 75 when limit hit (preserves system messages)
# Auto-cleanup after 24 hours inactivity
# Thread-safe with threading.Lock
```

### Tools (`tools.py`)

Two sample tools included: `get_weather` (simulated) and `calculate`.
We replace these with our pedagogical tools.

---

## 5. Context Injection — Our Implementation

This is where we modify the starter to inject lesson data.

### System prompt enrichment

When a request arrives, we read the `channel` from `context` to look up
the student's lesson data (from Contract 5: ConvoAIAgentConfig):

```python
async def enrich_system_prompt(
    messages: list[dict],
    channel: str,
) -> list[dict]:
    """Inject lesson context into the system prompt."""
    # Look up lesson data by channel name
    # Channel format: lesson_{lesson_id}_practice_{student_id}
    lesson_data = await get_lesson_context(channel)

    if not lesson_data:
        return messages

    context_block = build_context_block(lesson_data)

    # Prepend context to existing system message
    enriched = []
    for msg in messages:
        if msg["role"] == "system":
            enriched.append({
                "role": "system",
                "content": f"{msg['content']}\n\n{context_block}"
            })
        else:
            enriched.append(msg)

    return enriched


def build_context_block(data: dict) -> str:
    """Build the lesson context block for the system prompt."""
    sections = []

    # Student info
    sections.append(f"""## Student Profile
- Name: {data['student_name']}
- Level: {data['student_level']} (CEFR)
- Native language: {data['language_pair']['l1']}
- Learning: {data['language_pair']['l2']}""")

    # Errors from the lesson
    if data.get('lesson_errors'):
        error_lines = []
        for err in data['lesson_errors']:
            error_lines.append(
                f"- [{err['type']}/{err['severity']}] "
                f"'{err['original']}' → '{err['corrected']}': {err['explanation']}"
            )
        sections.append(f"""## Lesson Errors (practice these)
{chr(10).join(error_lines)}""")

    # Themes from the lesson
    if data.get('lesson_themes'):
        theme_lines = [f"- {t['topic']}: {', '.join(t['vocabulary'][:5])}"
                       for t in data['lesson_themes']]
        sections.append(f"""## Lesson Topics
{chr(10).join(theme_lines)}""")

    # Quiz results (injected mid-conversation)
    if data.get('quiz_results'):
        sections.append(format_quiz_results(data['quiz_results']))

    return "\n\n".join(sections)
```

### Quiz result injection (mid-conversation)

When Classtime quiz results arrive (via our backend polling Pusher events),
we update the lesson context and the next LLM call picks it up:

```python
# In-memory store for quiz results per channel
quiz_results_store: dict[str, list[dict]] = {}

@app.post("/update-quiz-results")
async def update_quiz_results(channel: str, results: list[dict]):
    """Called by our Django backend when Classtime results arrive."""
    quiz_results_store[channel] = results
    return {"status": "ok"}
```

Alternative approach: Use the ConvoAI **Update Agent API** to modify
`system_messages` directly (see 01-agora-convoai.md § 3.3).

### Agent registration

The agent-samples backend can POST to `/register-agent` on startup:

```python
@app.post("/register-agent")
async def register_agent(request: dict):
    """Called when ConvoAI agent starts. Sets up lesson context."""
    channel = request.get("channel")
    app_id = request.get("app_id")
    # Pre-load lesson data for this channel
    lesson_data = await fetch_lesson_data_from_backend(channel)
    context_cache[channel] = lesson_data
    return {"status": "registered"}
```

---

## 6. Local Development

### Running the server

```bash
cd server-custom-llm/python
pip install -r requirements.txt
# Set env vars
export LLM_API_KEY=sk-your-openai-key
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

python -m uvicorn custom_llm:app --host 0.0.0.0 --port 8100
```

### Exposing to Agora cloud

ConvoAI runs in Agora's cloud, so it needs a public URL to reach our server.
Use cloudflared tunnel:

```bash
# Install: brew install cloudflared
cloudflared tunnel --url http://localhost:8100
# Returns: https://xxx-yyy.trycloudflare.com
```

Then set in your agent start config:
```json
"llm": {
  "url": "https://xxx-yyy.trycloudflare.com/chat/completions",
  "vendor": "custom"
}
```

### Testing the endpoint

```bash
curl -X POST http://localhost:8100/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "system", "content": "You are a language tutor."},
      {"role": "user", "content": "I goed to the store"}
    ],
    "stream": true,
    "context": {"channel": "test_channel"}
  }'
```

---

## 7. Environment Variables

```bash
# LLM provider
LLM_API_KEY=sk-your-key          # OpenAI API key
LLM_BASE_URL=https://api.openai.com/v1  # Or Anthropic, etc.
LLM_MODEL=gpt-4o-mini            # Default model

# Our backend (for fetching lesson data)
BACKEND_URL=http://localhost:8005  # Django backend
BACKEND_API_TOKEN=your-drf-token  # DRF Token auth

# Thymia (optional)
THYMIA_ENABLED=false
THYMIA_API_KEY=your-thymia-key
```

---

## 8. What We Modify from the Starter

| File | Change | Why |
|------|--------|-----|
| `custom_llm.py` | Add `enrich_system_prompt()` | Inject lesson errors, themes, level |
| `custom_llm.py` | Add `/update-quiz-results` endpoint | Receive quiz results from Django |
| `custom_llm.py` | Add `/register-agent` endpoint | Pre-load lesson context on agent start |
| `conversation_store.py` | No changes needed | Works as-is |
| `tools.py` | Replace sample tools with pedagogical tools | Grammar lookup, exercise suggestion |

### Our pedagogical tools

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "explain_grammar_rule",
            "description": "Look up and explain a grammar rule relevant to the student's error",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_type": {"type": "string", "description": "e.g., 'article_confusion', 'irregular_past'"},
                    "language": {"type": "string", "description": "Target language"}
                },
                "required": ["error_type", "language"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_practice_exercise",
            "description": "Suggest a specific practice exercise for the student's weak area",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_area": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["easier", "same", "harder"]}
                },
                "required": ["skill_area"]
            }
        }
    }
]
```

---

## 9. Data Flow: Quiz Results → Voice Adaptation

```
1. Student answers Classtime quiz question
2. Classtime fires Pusher event (student_response)
3. Our Django backend receives via Pusher websocket
4. Backend decodes result: "student got article question WRONG"
5. Backend calls Custom LLM: POST /update-quiz-results
   OR
   Backend calls ConvoAI: POST .../agents/{id}/update (system_messages)
6. Next time student speaks, Custom LLM includes quiz data in prompt
7. Avatar: "I see you found articles tricky on the quiz too.
   Let's practice — which article goes with 'university'?"
```

---

## References

- [server-custom-llm repo](https://github.com/AgoraIO-Conversational-AI/server-custom-llm)
- [ConvoAI Custom LLM docs](https://docs.agora.io/en/conversational-ai/develop/custom-llm)
- [agent-samples repo](https://github.com/AgoraIO-Conversational-AI/agent-samples)
