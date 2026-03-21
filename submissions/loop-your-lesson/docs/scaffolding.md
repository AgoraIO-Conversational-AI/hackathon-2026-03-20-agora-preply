# Scaffolding

Tech stack, project structure, and deep dive paths for the hackathon.
See [architecture.md](architecture.md) for how the systems connect end to end.

## Two repos + CLI bridge

We separate concerns into two repos with different CLAUDE.md contexts,
connected by a CLI layer:

| Repo | Purpose | CLAUDE.md tuned for |
|------|---------|---------------------|
| **preply-lesson-intelligence** | App: backend, frontend, extension, infra | Code development, Django patterns, testing |
| **preply-lesson-ai-skills** | Skills: AI workflows, theory, reference materials, CLI | Content quality, analysis depth, pedagogical rigor |

The skills repo is where you iterate on what the AI produces. The app repo is
where you build the system that runs it. Different mindsets, different guides.

### How they connect: the CLI layer

The skills repo includes a CLI (uv + Click) that bridges the two repos.
The CLI is a thin HTTP client - it authenticates with the backend and
pushes/pulls data via REST endpoints.

```
preply-lesson-ai-skills CLI                    preply-lesson-intelligence backend
────────────────────                    ────────────────────────────────────
preply-lesson-ai auth setup --api-key <token>      DRF Token Authentication
preply-lesson-ai auth verify                       GET /api/v1/lessons/?page_size=1

preply-lesson-ai transcripts fetch <lesson_id>     GET /api/v1/lessons/{id}/transcript/
preply-lesson-ai skill-results push <student_id>   POST /api/v1/skill-results/{student_id}/
preply-lesson-ai classtime-questions push <id>      POST /api/v1/classtime-sessions/questions/
preply-lesson-ai classtime-sessions create <qs_id>  POST /api/v1/classtime-sessions/
preply-lesson-ai classtime-sessions sync <code>     GET /api/v1/classtime-sessions/{code}/results/
preply-lesson-ai daily-briefing push <teacher_id>   POST /api/v1/daily-briefings/

preply-lesson-ai pipeline start <entity> <stage>    POST /api/v1/.../stages/{code}/start/
preply-lesson-ai pipeline complete <entity> <stage> POST /api/v1/.../stages/{code}/complete/
```

**Auth**: DRF token stored in `~/.preply-lesson-ai/config.json` with multi-environment
support (local/prod). Token passed as `Authorization: Token {key}` header.

**The workflow**:
1. Skill runs in the skills repo (via Claude Code slash command)
2. Skill reads theory/references, analyzes transcript, produces structured output
3. Skill calls CLI to push results to the app backend
4. App backend stores results, triggers Classtime session creation, etc.

**During hackathon**: skills call CLI commands directly. Fast iteration.

**Post-hackathon**: app's Temporal workers run skills programmatically, using
the same API endpoints the CLI calls.

### Worker (automation)

For automated skill execution, a worker process polls the backend:

```
Worker polls GET /api/v1/skill-executions/pending/ every 5s
  -> Picks up PENDING execution
  -> PATCHes status=RUNNING
  -> Spawns: claude -p /{skill_name} {params}
  -> Captures output
  -> PATCHes status=COMPLETED/FAILED with output_log
```

Skills run in the background. The frontend queries completed results via
the AI chat  - see [conversational-ux.md](conversational-ux.md).

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python, Django, DRF | Proven stack, fast to scaffold |
| Validation | Pydantic (strict, extra=forbid) | Type-safe service layer |
| AI | OpenAI / Anthropic Claude (flexible) | Analysis + question generation. OpenAI is a hackathon organizer |
| Workflows | Temporal | Durable skill execution, async pipelines |
| Database | PostgreSQL | Reliable, good JSON support |
| Cache/streams | Redis | SSE streaming, cache, pub/sub |
| Frontend | React, TypeScript, Vite, TailwindCSS | Fast dev, good DX |
| Extension | Chrome Manifest V3 | Lives on Preply, side panel |
| Assessment | Classtime API (JSON mode) | 11 question types, auto-grading |
| Voice practice | Agora ConvoAI | AI avatar voice practice, real-time adaptation |
| Real-time transport | Agora RTC + RTM | Audio/video streaming + real-time data messaging |
| Video avatar | Anam | Lip-synced video avatar for ConvoAI sessions |
| Voice biomarkers | Thymia | Stress, emotion, confidence detection from voice |
| Package mgmt | uv (Python), bun (Node) | Fast, modern |
| Process mgmt | mprocs | Single command starts everything |
| Quality | ruff (Python), ESLint (TS), pytest | Fast lint + test |
| CI/CD | GitHub Actions | Lint + test on PR, deploy on merge |

---

## App repo: preply-lesson-intelligence

CLAUDE.md here guides code development: Django patterns, thin views, Pydantic
validation, testing philosophy, commit conventions.

```
preply-lesson-intelligence/
│
├── .claude/
│   ├── settings.json
│   ├── settings.local.json
│   └── commands/
│       └── pr-description.md     # PR helper
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # ruff + eslint + pytest on PR
│       └── deploy.yml            # Deploy on merge to main
│
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   └── local.py
│   │   ├── urls.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── accounts/             # Preply <-> Classtime user mapping
│   │   ├── lessons/              # Transcripts, metadata, lesson history
│   │   ├── skill_results/         # Skill execution outputs (per-skill results)
│   │   ├── classtime_sessions/    # Classtime sessions, questions, results
│   │   └── extension/            # Chrome extension auth, context, proxy
│   ├── services/
│   │   ├── classtime/            # Classtime API client (JSON mode)
│   │   ├── skill_results/         # Skill result storage and retrieval
│   │   ├── classtime_sessions/    # Question generation + session creation
│   │   ├── convoai/            # Agora ConvoAI client (agent config, session management)
│   │   └── agora/              # Agora RTC/RTM token generation, channel management
│   ├── workflows/                # Temporal workflows + activities
│   │   ├── lesson_analysis.py
│   │   ├── classtime_session.py
│   │   └── activities.py
│   ├── stream/                   # SSE infrastructure
│   │   ├── events.py
│   │   └── sse.py
│   ├── manage.py
│   ├── pyproject.toml
│   └── conftest.py
│
├── frontend/
│   ├── src/
│   │   ├── api/                  # API client, SSE streaming, hooks
│   │   ├── components/           # Shared UI
│   │   ├── views/
│   │   │   ├── DailyBriefing/     # Teacher morning overview
│   │   │   ├── PracticeAssistant/ # Student practice + AI chat
│   │   │   ├── ClasstimeSession/  # Classtime dashboard embed
│   │   │   └── VoicePractice/      # ConvoAI avatar practice session UI
│   │   ├── lib/                  # Extension context, auth provider
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── chrome_extension/              # Chrome Manifest V3
│   ├── manifest.json
│   ├── background.js             # Service worker
│   ├── content-script.js         # Preply page context
│   └── libs/
│       ├── config.js
│       ├── auth.js
│       └── contextExtractor.js
│
├── docs/                         # All project documentation
│   ├── pitch.md
│   ├── pitch-full.md
│   ├── prd.md
│   ├── architecture.md
│   ├── scaffolding.md            # This file
│   ├── skill-system.md
│   ├── conversational-ux.md
│   └── classtime-api-guide.md
│
├── docker-compose.yml            # PostgreSQL, Redis, Temporal, Temporal UI
├── Makefile
├── bin/
│   ├── start
│   ├── mprocs.yaml
│   └── temporal-worker
├── CLAUDE.md                     # Tuned for code development
├── CLAUDE.local.md               # Gitignored
├── README.md
├── .env.example
└── .pre-commit-config.yaml
```

---

## Skills repo: preply-lesson-ai-skills

CLAUDE.md here guides content quality: analysis depth, pedagogical rigor,
reference material usage, output validation. The AI should produce
pedagogically sound output, not just plausible-looking text.

```
preply-lesson-ai-skills/
│
├── .claude/
│   ├── settings.json
│   ├── settings.local.json
│   └── skills/                   # AI skills (reasoning + theory)
│       ├── analyze-lesson-errors/
│       │   ├── SKILL.md
│       │   └── references/
│       ├── analyze-lesson-themes/
│       │   └── SKILL.md
│       ├── analyze-lesson-level/
│       │   ├── SKILL.md
│       │   └── references/
│       ├── generate-classtime-questions/
│       │   ├── SKILL.md
│       │   └── references/
│       ├── configure-practice-agent/
│       │   ├── SKILL.md
│       │   └── references/
│       └── prepare-daily-briefing/
│           └── SKILL.md
│
├── src/
│   └── lesson_ai/               # CLI package
│       ├── __init__.py
│       ├── cli.py                # Click CLI entry point
│       ├── commands/
│       │   ├── auth.py           # auth setup, verify, use, status
│       │   ├── transcript.py     # fetch, list transcripts
│       │   ├── skill_results.py   # push skill results
│       │   ├── classtime.py       # push questions, create session, sync results
│       │   ├── stage.py          # start/complete stages
│       │   ├── prep.py           # push prep briefs
│       │   └── convoai.py      # configure agent, create session, sync results
│       ├── client.py             # HTTP client (httpx) to app backend
│       └── config.py             # Config + token storage (~/.preply-lesson-ai/config.json)
│
├── theory/                       # Reference materials that skills read
│   ├── error-taxonomy/
│   ├── cefr-levels/
│   ├── interlanguage/
│   ├── question-design/
│   └── progress-tracking/
│
├── storage/                      # Skill inputs and outputs (local)
│   ├── transcripts/
│   │   └── {student_id}/
│   │       └── {lesson_date}/
│   ├── skill-results/
│   │   └── {student_id}/
│   │       └── {lesson_date}/
│   ├── questions/
│   │   └── {student_id}/
│   │       └── {lesson_date}/
│   └── prep-briefs/
│       └── {student_id}/
│
├── worker/                       # Skill worker (polls for pending executions)
│   └── skill_worker.py
│
├── pyproject.toml                # uv + click, entry point: lesson-ai
├── claude.md                     # Tuned for analysis quality + pedagogy
├── claude.local.md               # Gitignored
└── readme.md
```

### CLI entry point

```toml
# pyproject.toml
[project.scripts]
preply-lesson-ai = "lesson_ai.cli:cli"
```

```python
# src/lesson_ai/cli.py
@click.group()
@click.option('--auth', type=click.Choice(['local', 'prod']))
def cli(auth):
    """Lesson AI - skills CLI for lesson analysis and Classtime session management"""
    if auth:
        set_env_override(auth)

cli.add_command(auth_group, 'auth')
cli.add_command(transcripts_group, 'transcripts')
cli.add_command(skill_results_group, 'skill-results')
cli.add_command(classtime_questions_group, 'classtime-questions')
cli.add_command(classtime_sessions_group, 'classtime-sessions')
cli.add_command(daily_briefing_group, 'daily-briefing')
cli.add_command(pipeline_group, 'pipeline')
cli.add_command(convoai_group, 'convoai')
```

### Config storage

```json
// ~/.preply-lesson-ai/config.json
{
  "environments": {
    "local": {
      "api_key": "Token abc123...",
      "api_url": "http://localhost:8005/api/v1"
    },
    "prod": {
      "api_key": "Token xyz789...",
      "api_url": "https://app.example.com/api/v1"
    }
  },
  "active_env": "local"
}
```

### How the two repos connect

```
preply-lesson-ai-skills                     preply-lesson-intelligence
─────────────────────────────────    ──────────────────────────────
.claude/skills/ run via Claude Code  Backend API receives results
    ↓                                    ↑
CLI: preply-lesson-ai skill-results push      --->  POST /api/v1/skill-results/
CLI: preply-lesson-ai classtime-questions push --->  POST /api/v1/classtime-sessions/questions/
CLI: preply-lesson-ai classtime-sessions create --->  POST /api/v1/classtime-sessions/
CLI: preply-lesson-ai classtime-sessions sync  <---  GET  /api/v1/classtime-sessions/.../results/
CLI: preply-lesson-ai daily-briefing push      --->  POST /api/v1/daily-briefings/
    ↓                                    ↓
theory/ guides skill quality         SSE streams progress to extension
storage/ holds local I/O             PostgreSQL stores everything
worker/ automates execution          Frontend shows results to teacher
```

During the hackathon, a teammate iterates on skill quality in the skills
repo using Claude Code while another builds the app infrastructure. The CLI
bridges them - skills produce structured JSON, CLI pushes it to the app.

For how skills are structured, executed, tracked, and what research is
needed, see [skill-system.md](skill-system.md). For how the AI chat works
(modes, tools, widgets), see [conversational-ux.md](conversational-ux.md).

