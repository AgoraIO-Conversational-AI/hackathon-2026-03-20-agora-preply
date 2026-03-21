# Loop Your Lesson

## Project structure

- `backend/` - Django REST Framework + PostgreSQL
- `frontend/` - React + Vite + TypeScript + Tailwind
- `chrome_extension/` - Chrome Manifest V3, side panel (coming)
- `docs/` - Architecture, skills, conversational UX, Classtime API

## Key concepts

- Skills run automatically in the background - no teacher triggering required
- Query tools read from completed skill outputs (`SkillExecution.output_data`)
- Two AI chat modes: `daily_briefing` (teacher), `student_practice` (student)
- Dual-return pattern: every tool returns `(message, data)` - message for LLM, data for widget
- See `docs/conversational-ux.md` for the full interaction model

## Backend patterns

- Keep views thin - business logic in services
- Pydantic for validation (strict, `extra=forbid`)
- Imports at top of files

## Service patterns

Services are function-based (not classes, except Classtime HTTP client and ConvoAI client).
Each app owns its domain services in `apps/{app}/services.py` or `apps/{app}/services/`.
Cross-app services live in `services/` (pipeline, agora, convoai).

- `apps/lessons/services.py` - lesson lifecycle
- `apps/skill_results/services.py` - execution state machine
- `apps/daily_briefings/services.py` - briefing storage
- `apps/classtime_sessions/services/` - Classtime API (client, auth, questions, sessions, results)
- `apps/conversations/services/` - AI chat (agent loop, tools, modes, query tools)
- `apps/voice_sessions/` - voice practice session models
- `services/pipeline.py` - cross-domain orchestration
- `services/convoai/` - Agora ConvoAI agent (client, context, quiz bridge, Thymia, views)
- `services/agora/` - Agora RTC token generation

Views call services. Services call models. Services raise domain exceptions;
views map them to HTTP status codes.

## Testing

```bash
make test                                    # full backend suite
cd backend && uv run pytest path/to/test.py  # specific file
cd backend && uv run pytest -k "feature"     # by keyword
cd backend && uv run pytest --lf             # re-run failures only
```

- Tests in `apps/{app}/tests/` or `backend/tests/`
- Use `@pytest.mark.django_db` for database tests
- Use factories (factory-boy), not direct model creation
- One test per behavior, quality over quantity

## Style guide

- Sentence case for headers
- Be brief - don't repeat what code shows
- Use `-` (hyphen), never em dash
- Present tense commits: "Add feature" not "Added feature"
- No AI attribution, no Co-Authored-By in commits
