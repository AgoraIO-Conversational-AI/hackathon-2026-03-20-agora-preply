# Deep dives

Production-proven patterns adapted for Preply Lesson Intelligence, inspired
by [PostHog's Max AI assistant](https://github.com/PostHog/posthog) (`ee/hogai/`).

Each deep dive shows: what PostHog does, what we take, what we skip (and why).

## Reading order

Start at 01 and work through. Foundations first, then the AI pipeline, then delivery.

| # | Deep dive | What it covers | PostHog source |
|---|-----------|---------------|----------------|
| 01 | [Django patterns](01-django-patterns.md) | Models, services, exceptions, Pydantic validation | [`posthog/models/utils.py`](https://github.com/PostHog/posthog/blob/master/posthog/models/utils.py) |
| 02 | [State persistence](02-state-persistence.md) | SkillExecution state machine, two-repo model, DailyBriefing | [`ee/models/assistant.py`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py) |
| 03 | [Tool system](03-tool-system.md) | PreplyTool, dual-return `(message, data)`, QueryRunner registry | [`ee/hogai/tool.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/tool.py) |
| 04 | [Agent loop](04-agent-loop.md) | While-loop agent, tool dispatch, extensible mode system | [`ee/hogai/core/`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/) |
| 05 | [Context injection](05-context-injection.md) | 4-layer context (Subject, Student, Lesson, Pedagogical) | [`ee/hogai/llm.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/llm.py) |
| 06 | [Streaming](06-streaming.md) | SSE events, message merging, trust layers | [`ee/hogai/core/stream_processor.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/stream_processor.py) |
| 07 | [Trust and transparency](07-trust-and-transparency.md) | Trust stack (WHY/WHAT/WHERE/HOW), progressive disclosure | [`ee/hogai/utils/types/`](https://github.com/PostHog/posthog/blob/master/ee/hogai/utils/types/) |
| 08 | [Frontend UX](08-frontend-ux.md) | Widgets, modes, loading states, ProcessTimeline | [`ee/hogai/core/stream_processor.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/stream_processor.py) |
| 09 | [Visual design system](09-visual-design-system.md) | Colors, typography, spacing, animation, accessibility | Preply production site, Tailwind CSS v4 |

## How to use these docs

**During implementation**: each deep dive ends with an "Implementation notes"
section listing exact file paths and patterns to follow.

**Key insight from PostHog**: they built a sophisticated AI agent with
LangGraph, Temporal, Redis Streams, and 70+ tools. Their own recommendation?
Skip frameworks, use a simple while-loop, add complexity only when needed.
We follow that advice.

## What makes our approach unique

PostHog analyzes product data. We analyze teaching. Our competitive advantage
is **pedagogically grounded reasoning**: every error categorized against
established error taxonomy, every level assessed against CEFR descriptors,
every question designed with learning theory. The `reasoning` field in every
skill output is what turns generic AI into a trusted teaching assistant.
