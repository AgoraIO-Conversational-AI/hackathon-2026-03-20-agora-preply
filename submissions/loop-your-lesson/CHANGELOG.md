# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] — Track 2: Voice Practice Implementation

### Added — Backend Services
- `backend/services/agora/tokens.py` — Agora RTC token generation (unique channel per session)
- `backend/services/convoai/client.py` — ConvoAI REST API client (start/stop/update/speak/interrupt/get_history)
- `backend/services/convoai/schemas.py` — Pydantic models (VoiceSessionStart, MasteryState, BiomarkerState, AgentResponse)
- `backend/services/convoai/context.py` — 4-layer system prompt builder with mastery + biomarker enrichment
- `backend/services/convoai/views.py` — Django async views for voice session API endpoints
- `backend/services/convoai/session_store.py` — Redis session store with in-memory fallback
- `backend/services/convoai/quiz_bridge.py` — Pusher listener + protobuf decoder + quiz-to-mastery-to-agent pipeline
- `backend/services/convoai/thymia.py` — Thymia Sentinel SDK client + student_monitor policy integration
- `backend/apps/voice_sessions/` — VoiceSession Django model for persisting session results

### Added — API Endpoints
- `POST /api/v1/voice-sessions/` — Start voice practice session (creates ConvoAI agent)
- `GET /api/v1/voice-sessions/{id}/` — Get session status
- `POST /api/v1/voice-sessions/{id}/stop/` — Stop session and agent
- `POST /api/v1/voice-sessions/{id}/frame/` — Video biomarker endpoint (stub)
- `POST /api/v1/voice-sessions/{id}/biomarkers/` — Receive Thymia biomarker scores
- `GET /api/v1/voice-sessions/{id}/context/` — Debug: inspect current system prompt + mastery + conversation history

### Added — Frontend
- `frontend/src/views/VoicePractice/AnamAvatar.tsx` — Avatar component with mic mute/unmute controls
- `frontend/src/views/VoicePractice/useVoiceSession.ts` — Session lifecycle hook
- `frontend/src/views/VoicePractice/useAgoraRTC.ts` — Agora RTC audio connection with mute support
- `frontend/src/services/voiceApi.ts` — API client for voice session endpoints
- Integrated voice avatar into `ShowcaseClasstime.tsx` PracticeModal (side-by-side quiz + avatar)

### Added — Tests
- `backend/tests/test_context.py` — 12 tests for context builder (prompt structure, quiz results, biomarkers)
- `backend/tests/test_schemas.py` — 10 tests for Pydantic validation (extra=forbid, required fields, defaults)
- `backend/tests/test_tokens.py` — 3 tests for token generation (unique channels, format)

### Added — Dependencies
- `agora-token-builder` — RTC token generation
- `pysher` — Pusher websocket client for real-time quiz events
- `thymia-sentinel` — Real-time voice biomarker streaming SDK
- `uvicorn` — ASGI server for proper async support (replaces Django runserver)
- `agora-rtc-sdk-ng` (frontend) — Agora RTC SDK

### Added — Configuration
- Agora env vars (APP_ID, APP_CERTIFICATE, CUSTOMER_ID, CUSTOMER_SECRET)
- ElevenLabs TTS (ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID)
- Thymia (THYMIA_API_KEY, THYMIA_BASE_URL)
- OpenAI (OPENAI_API_KEY)
- Django logging config (console + file rotation)

### Architecture Decisions
- **Native OpenAI** via ConvoAI (`style: "openai"`, `gpt-4o-mini`) — all hackathon sponsors aligned
- **ElevenLabs TTS** (`eleven_flash_v2_5`) — Microsoft TTS requires Azure key, ElevenLabs works with just API key
- **Semantic turn detection** — replaces deprecated `enable_aivad`, uses understanding-based end-of-speech
- **Pusher websockets** for real-time quiz events from Classtime
- **`/update` + `/speak` (APPEND)** for runtime context injection and instant quiz reactions
- **Thymia Sentinel SDK** with `student_monitor` policy — real-time streaming, actionable tutor recommendations
- **Unique channel names** per session (UUID suffix) — prevents 409 Conflict on rapid start/stop
- **uvicorn ASGI** instead of Django runserver — proper async event loop for httpx + Redis
- **Redis session store** with in-memory fallback — graceful degradation if Redis is down

### Known Issues
- Django `runserver` has stale event loop issues with async views — use `uvicorn` instead
- Classtime iframe blocked by Google OAuth (cross-origin) — quiz opens in popup or uses auth token URL
- Anam video avatar not yet integrated — placeholder with audio indicator

---

## [bec137a] — 2026-03-21 — Track 1: Core Scaffold (Vasyl)

### Added
- Django backend: 8 apps, all models with UUID PKs, API stubs
- React frontend: design system, chat UI, widgets, TypeScript types
- Infrastructure: Docker (PostgreSQL, Redis, Temporal), mprocs, Makefile

---

## [ec42e44] — 2026-03-20 — Documentation

### Added
- Project docs: pitch, architecture, deep dives, API guides
- Classtime API guide with Pusher real-time events
