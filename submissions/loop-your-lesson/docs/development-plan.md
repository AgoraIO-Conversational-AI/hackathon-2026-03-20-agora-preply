# Development plan

Team Loop. Two tracks, shared contracts. See [architecture.md](architecture.md)
for how systems connect.

## Tracks overview

```
Track 1: CORE (Vasyl)                    Track 2: VOICE PRACTICE (Andrew)
──────────────────────                   ────────────────────────────────
Backend (Django, API, models)            Agora ConvoAI agent setup
AI skills (errors, themes, level)        Lesson context → agent knows student's mistakes
Classtime integration + pipeline         Classtime quiz results → shape the conversation
AI chat (agent loop, tools, SSE)         Anam avatar (visual presence)
Frontend (chat UI, widgets)              Voice practice UX
Chrome extension                         Integration with Core backend
Demo data + demo script
```

---

## Track 1: Core (Vasyl)

### Phase 1: Scaffolding + skills

**Goal: repos runnable, core models in DB, first skill producing output**

- Django project, docker-compose (PostgreSQL, Redis), mprocs
- Core models + migrations:
  - `accounts`: Teacher, Student
  - `tutoring`: TutoringRelationship (subject, level, goal, schedule)
  - `lessons`: Lesson (subject_type, subject_config), LessonStudent
  - `skill_results`: SkillExecution (nullable student, teacher FK)
  - `classtime_sessions`: ClasstimeSession, SessionParticipant
  - `daily_briefings`: DailyBriefing
- API skeleton: endpoints from Contract 3 with DRF viewsets + token auth
- Skills repo: pyproject.toml with Click CLI, skill directory structure
- Error taxonomy + CEFR reference materials in `theory/`
- First skill: `analyze-lesson-errors` producing valid Contract 1 JSON

**Done when**: `mprocs` starts everything, API returns JSON, first skill
output pushed to backend.

### Phase 2: Classtime integration + pipeline

**Goal: skill output → Classtime session, end to end**

- Classtime API client: account linking, question sets, sessions
- Pipeline: lesson created → skills run → questions generated → session created
- `generate-classtime-questions` skill: maps errors to question types
  (fill-in-gap for conjugation, sorter for word order, categorizer for vocab)
- 1 sample transcript + skill output for testing
- Verify: JSON in → working Classtime session out

**Done when**: pushing skill output creates a Classtime session with real
questions a student can answer.

**Sync with Andrew**: share skill output format so he can inject it into
the ConvoAI agent.

### Phase 3: AI chat + frontend

**Goal: agent loop working, query tools returning real data, chat UI usable**

- Agent loop: while-loop with Claude API, tool execution, SSE streaming
- Query tools: `query_errors`, `query_themes`, `query_level`, `query_schedule`
- Context injection: subject-aware pedagogical context
- Student practice mode + teacher daily briefing mode
- Widgets: ErrorAnalysisWidget, PracticeCardWidget, ScheduleWidget
- Chat frontend: input, message list, SSE consumer, widget rendering
- Chrome extension: side panel loads chat iframe

**Done when**: can chat with the AI, ask about errors, teacher sees
daily briefing with student progress.

### Phase 4: Integration + demo

**Goal: demo-ready, smooth happy path**

- Full loop: transcript → analysis → Classtime → voice practice → briefing
- Connect ConvoAI session links into the student flow (from Andrew)
- Trust layers: reasoning display, tool step expansion
- Demo data: 3-5 students with varied levels, goals, practice results
- Demo script: the story we tell judges

**Done when**: a judge can watch the full loop from lesson to briefing.

---

## Track 2: Voice Practice (Andrew)

### What this track delivers

A student finishes a lesson. They open a voice practice session and talk
with an AI avatar that knows what they got wrong. If they just bombed
articles on the Classtime quiz, the avatar steers the conversation toward
articles. The student speaks, the avatar responds — real conversation built
from real lesson data.

### Phase 1: Get an agent talking

**Goal: a ConvoAI agent that a student can have a voice conversation with**

- Agora ConvoAI setup: API client, agent creation, token generation
- Student connects via Agora RTC, agent joins the channel
- Basic conversation works: student speaks → agent responds
- Anam avatar: video avatar with lip-sync on the agent's speech

**Done when**: open a browser, see an avatar, have a conversation.

### Phase 2: Inject lesson context

**Goal: the agent knows what the student got wrong**

- Accept skill output from Core backend (Contract 1: errors, themes, level)
- Build a system prompt from the student's actual lesson data:
  errors they made, topics they covered, their assessed level
- The agent references specific mistakes: "I noticed you used 'goed'
  instead of 'went' — let's practice irregular past tenses"
- Configure conversation plan: which errors to cover, in what order

**Done when**: give the agent a student's error analysis, have a conversation
where it meaningfully uses that data.

**Sync with Vasyl**: agree on how skill outputs get passed to the agent
(Contract 5).

### Phase 3: Feed quiz results into the conversation

**Goal: Classtime quiz answers shape what the avatar talks about**

- Poll or receive Classtime session results from Core backend
- When quiz results come in, update the agent's context:
  wrong on articles → avatar pivots to article practice
  aced conjugation → avatar skips that, moves to harder topics
- The conversation adapts as the student works through both surfaces

**Done when**: student answers Classtime questions, avatar's conversation
shifts based on what they got right/wrong.

### Phase 4: Polish + integration

**Goal: the voice practice experience feels good to demo**

- Smooth handoff from Classtime to voice practice in the UI
- Session results (what was practiced, how it went) flow back to Core
  backend so the teacher briefing includes voice practice data
- Handle edge cases: agent interrupted, connection drops, empty skill output
- Voice/avatar quality: TTS voice selection, avatar persona

**Done when**: voice practice is part of the demo happy path, end to end.

---

## Integration contracts

Define early, build independently.

### Contract 1: Skill output JSON

Skills produce JSON stored in `SkillExecution.output_data`.

```python
ErrorOutput = {
    "errors": [{
        "type": str,             # "grammar", "vocabulary", "pronunciation", "fluency"
        "severity": Severity,    # minor, moderate, major
        "original": str,         # what student said
        "corrected": str,        # what it should be
        "explanation": str,      # human-readable correction
        "reasoning": str,        # why categorized this way
        "position": { "utterance": int, "timestamp": str }
    }],
    "summary": { "total": int, "by_type": dict, "most_frequent": str }
}

ThemeOutput = {
    "themes": [{
        "topic": str,
        "vocabulary": [str],
        "utterance_count": int,
        "transcript_range": { "start": str, "end": str }
    }]
}

LevelOutput = {
    "level": str,            # e.g. "B1"
    "framework": str | None, # "CEFR" for language
    "strengths": [str],
    "gaps": [str],
    "suggestions": [str]
}
```

### Contract 2: Transcript JSON

```python
Transcript = {
    "lesson_id": str,
    "student_ids": list[str],
    "teacher_id": str,
    "subject_type": str,        # "language"
    "subject_config": dict,     # {"language_pair": "es-en", "l1": "Spanish", "l2": "English"}
    "date": str,
    "duration_minutes": int,
    "utterances": [{
        "speaker": str,
        "text": str,
        "timestamp": str
    }]
}
```

### Contract 3: Backend API

```
# Lessons
POST /api/v1/lessons/                           <- Push lesson
GET  /api/v1/lessons/{id}/transcript/           <- Fetch transcript
GET  /api/v1/lessons/{id}/skill-results/        <- Lesson-scoped skill results

# Skill results
POST /api/v1/skill-results/                     <- Push skill output
GET  /api/v1/students/{id}/skill-results/       <- Student-scoped results

# Classtime sessions
POST /api/v1/classtime-sessions/                <- Create session
GET  /api/v1/classtime-sessions/{code}/results/ <- Sync results

# Daily briefings
GET  /api/v1/daily-briefings/{teacher_id}/      <- Query briefing

# Conversations
POST /api/v1/conversations/                     <- Start conversation
POST /api/v1/conversations/{id}/stream/         <- Continue (SSE)
```

### Contract 4: Extension context

```typescript
interface ExtensionContext {
    teacher_id: string
    teacher_name: string
    student_ids?: string[]
    student_names?: string[]
    lesson_id?: string
    page_type: 'dashboard' | 'student' | 'lesson'
    subject_type?: string
}
```

### Contract 5: ConvoAI agent config

What Core passes to the voice practice system so the agent knows the student.

```python
ConvoAIAgentConfig = {
    "student_id": str,
    "student_name": str,
    "student_level": str,              # e.g. "B1"
    "lesson_errors": list[dict],       # From analyze-lesson-errors (Contract 1)
    "lesson_themes": list[dict],       # From analyze-lesson-themes (Contract 1)
    "classtime_session_code": str,     # So voice practice can poll quiz results
    "language_pair": dict,             # {"l1": "Spanish", "l2": "English"}
}
```

---

## Stretch goals

Things we'd love to have but won't block the demo.

| Goal | What it adds | Owner |
|------|-------------|-------|
| Thymia voice biomarkers | Avatar detects stress/confidence from voice, adapts pace | Andrew |
| Live lesson transcription | Real-time error detection during an Agora RTC lesson | Andrew |
| Cross-session gap analysis | What the student avoids, what's unpracticed across lessons | Vasyl |
| Offline lesson upload | Teacher uploads a recording from Zoom/WhatsApp/in-person | Vasyl |

---

## Risk mitigation

| Risk | Mitigation |
|------|-----------|
| Skills produce bad output | Sample transcript + expected output; iterate fast |
| Classtime API issues | Vasyl has full API access + experience; test early |
| ConvoAI agent feels generic | Inject real errors into system prompt; test with real skill output |
| Avatar doesn't feel right | Fall back to audio-only; avatar is a bonus, not the core value |
| Integration between tracks breaks | Contract 5 defined before coding; sync after each phase |
| Demo falls apart | Seed data ready; each track demo-able independently |

---

## Demo script

The story we tell judges. One student, one lesson, one loop.

1. **Lesson happened** — Maria had a Spanish→English lesson. Transcript available.
2. **System analyzed it** — errors found: article confusion, irregular past tense,
   vocabulary gaps around daily routines. Level: B1.
3. **Classtime session created** — 8 exercises built from Maria's actual mistakes.
   Fill-in-gap for conjugation, sorter for word order, categorizer for vocabulary.
4. **Maria does the quiz** — gets 6/8. Nails conjugation, struggles with articles.
5. **Maria opens voice practice** — avatar greets her, knows her lesson.
   "Let's talk about your morning routine — and pay attention to articles."
   Maria speaks, avatar responds, conversation naturally covers her weak spots.
6. **Teacher checks in next morning** — opens the briefing. Sees Maria: quiz 6/8,
   voice practice covered articles and daily routines, suggested focus for next
   lesson: articles in context.
7. **The loop closes** — next lesson starts where this one left off.
