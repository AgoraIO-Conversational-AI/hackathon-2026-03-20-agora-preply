# Context injection

> Inspired by [PostHog's Max AI assistant](https://github.com/PostHog/posthog).
> Source: [`ee/hogai/llm.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/llm.py)

## At a glance

**What this covers**: The 4-layer context system injected into the system prompt before each conversation, making the AI subject-aware and pedagogically grounded.

**Why it matters**: Context turns a generic AI into a teaching assistant that knows the student's level, the lesson's subject, and the right error taxonomy. Without context, the AI guesses. With it, the AI reasons.

**Key terms**:

| Term | Meaning |
|------|---------|
| Subject context | What's being taught - subject_type (language/math/art) + subject_config (language_pair, domain) |
| Student context | Who's learning - from TutoringRelationship: level, goal, l1/l2 |
| Lesson context | What happened - transcript summary, date, duration, utterance count |
| Pedagogical context | What framework to apply - error types per subject, severity levels, question types |
| TutoringRelationship | The ongoing teacher-student engagement. Richest context source (level, goal, schedule) |
| Prompt caching | Context placed as stable prefix → LLM caches it across turns |

**Prerequisites**: Data model in [classtime-api-guide.md](../classtime-api-guide.md)

---

## What PostHog does

PostHog injects context through a 4-layer system that transforms a generic LLM
into a product analyst that understands the user's data, org, and workflow.

| Layer | What it provides | Source |
|-------|-----------------|--------|
| **UI Context** | What the user is looking at (dashboards, insights, filters) | `AssistantContextManager._format_ui_context()` |
| **Schema Context** | What fields and values exist (events, properties, actions) | `_get_contextual_tools_prompt()` |
| **Account Context** | Who is asking (org name, user name/email, project timezone) | `MaxChatMixin._get_project_org_user_variables()` |
| **Mode Context** | What mode the agent is in (Analytics, SQL, Replay) | `_get_mode_context_messages()` |

### Account context: `MaxChatMixin`

[`MaxChatMixin`](https://github.com/PostHog/posthog/blob/master/ee/hogai/llm.py)
is mixed into both `MaxChatOpenAI` and `MaxChatAnthropic`, ensuring every LLM
call automatically carries project/org/user context via Mustache templates:

```python
PROJECT_ORG_USER_CONTEXT_PROMPT = """
You are currently in project {{{project_name}}}, which is part of the {{{organization_name}}} organization.
The user's name appears to be {{{user_full_name}}} ({{{user_email}}}). Feel free to use their first name when greeting. DO NOT use this name if it appears possibly fake.
All PostHog app URLs (known by domains us.posthog.com, eu.posthog.com, app.posthog.com) must use absolute paths without a domain, and omitting the `/project/:id/` prefix.
Use Markdown, for example "Find cohorts [in the Cohorts view](/cohorts)".
Current time in the project's timezone, {{{project_timezone}}}: {{{project_datetime}}}.
""".strip()
```

Variables are resolved from Django models (`self.team`, `self.user`) via
`_get_project_org_user_variables()`.

### Message enrichment: `_enrich_messages()`

Context is inserted at the end of the system messages block, before the first
non-system message. Stable system prompt prefix = LLM prompt cache hits.

```python
def _enrich_messages(self, messages: list[list[BaseMessage]], project_org_user_variables: dict[str, Any]):
    messages = messages.copy()
    for i in range(len(messages)):
        message_sublist = messages[i]
        for msg_index, msg in enumerate(message_sublist):
            if isinstance(msg, SystemMessage):
                continue  # Keep going
            else:
                # End of the system messages block
                copied_list = message_sublist.copy()
                copied_list.insert(msg_index, self._get_project_org_system_message(project_org_user_variables))
                messages[i] = copied_list
                break
    return messages
```

Both `generate()` and `agenerate()` call `_enrich_messages()` when
`inject_context=True` (the default). The async path uses `sync_to_async` to
safely read Django ORM objects.

### UI context assembly

The heavier context layers live in `AssistantContextManager`, using Mustache
templates wrapped in XML tags, parallel fetching with `asyncio.gather()` and a
semaphore (max 5 concurrent), and deduplication to avoid re-injecting context:

```python
ROOT_UI_CONTEXT_PROMPT = """
<attached_context>
{{{ui_context_dashboard}}}
{{{ui_context_insights}}}
{{{ui_context_events}}}
{{{ui_context_actions}}}
</attached_context>
<system_reminder>
The user can provide additional context in the <attached_context> tag.
</system_reminder>
"""
```

---

## What we take

We adapt PostHog's 4-layer approach to tutoring. Same principle: inject
structured domain knowledge so the LLM reasons about _this student's lesson_
rather than generic pedagogy.

| Layer | PostHog equivalent | What it provides |
|-------|-------------------|-----------------|
| **Subject Context** | Mode Context | Subject type and config drive everything: error taxonomies, level frameworks, question types |
| **Student Context** | Account Context | From `TutoringRelationship`: level, goal, L1/L2, lesson history |
| **Lesson Context** | UI Context | Current lesson: transcript summary, date, duration, utterance count |
| **Pedagogical Context** | Schema Context | Error types per subject, severity levels, level framework, question types |

### Layer 1: Subject Context

The subject drives the entire context tree. Language loads CEFR + grammar error
types; math would load grade levels + computational error types.

```python
class SubjectContext(BaseModel):
    """Drives error taxonomies, level frameworks, and question types."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_type: str                          # "language", "math", "music"
    subject_config: dict[str, str] = Field(    # e.g. {"language_pair": "es-en", "l1": "Spanish", "l2": "English"}
        default_factory=dict,
    )
```

### Layer 2: Student Context

Pulled from `TutoringRelationship`, updated after every lesson.

```python
class StudentContext(BaseModel):
    """Student being discussed. From TutoringRelationship + Student."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    student_id: str
    student_name: str
    l1: str | None = None                # Native language (language subjects)
    l2: str | None = None                # Learning language (language subjects)
    level: str | None = None             # Current assessed level ("B1", "grade_10")
    goal: str | None = None              # "Business English fluency", "Pass IELTS"
    total_lessons: int = 0
    schedule_description: str | None = None  # "Mon/Wed 10:00"
```

`TutoringRelationship` (one per teacher-student-subject combination) carries
`subject_type`, `subject_config`, `current_level`, `goal`,
`schedule_description`, `total_lessons`, and `last_lesson_at`. This single
model populates both `SubjectContext` and `StudentContext`.

### Layer 3: Lesson Context

Summary-level data. Full transcript stays out of the system prompt (10K+
tokens); a 200-300 token summary goes in, `get_transcript_segment` provides
on-demand access.

```python
class LessonContext(BaseModel):
    """Current lesson being analyzed."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    lesson_id: str
    transcript_summary: str | None = None   # 200-300 tokens, generated during pre-fetch
    lesson_date: str | None = None
    duration_minutes: int | None = None
    utterance_count: int = 0
```

### Layer 4: Pedagogical Context

The schema that grounds AI reasoning. Loaded once per subject type, stable
across conversations. PostHog's equivalent: schema context (events, properties).

```python
class PedagogicalContext(BaseModel):
    """Error taxonomy and level framework for this subject."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_type: str
    error_types: list[str] = Field(default_factory=list)
    severity_levels: list[Severity] = Field(
        default_factory=lambda: list(Severity),
    )
    level_framework: str | None = None       # "CEFR" for language, None for others
    question_types: list[QuestionType] = Field(
        default_factory=lambda: list(QuestionType),
    )
```

For a language subject, `error_types` resolves to
`["grammar", "vocabulary", "pronunciation", "fluency"]` and
`level_framework` to `"CEFR"`.

### How context appears in the system prompt

All four layers render into a stable markdown block at the top of the system
prompt. Stable prefix = prompt cache hits, same principle as PostHog.

```
## Current lesson
- Subject: language (Spanish L1 -> English L2)
- Student: Maria Garcia (student_42)
- Level: B1 (CEFR)
- Goal: Conversational fluency
- Schedule: Mon/Wed 10:00 (12 lessons total)
- Lesson: March 18, 2026 (50 min, 127 utterances)
- Summary: Covered travel planning and restaurant vocabulary. Teacher
  focused on past tense narrative and directions. Student engaged but
  consistent errors with past simple and articles.

## Pedagogical schema
- Subject: language
- Error types: grammar, vocabulary, pronunciation, fluency
- Severity: minor (expected at level), moderate (should be acquired), major (blocks communication)
- Level framework: CEFR (A1-C2)
- Question types: fill_gap, sorter, categorizer, single_choice, multiple_choice, boolean, cloze
```

Mode instructions (`DAILY_BRIEFING_INSTRUCTIONS`, `STUDENT_PRACTICE_INSTRUCTIONS`)
follow after. Context prefix stays identical across turns, maximizing cache hits.

---

## What we skip (and why)

### Mustache templates

PostHog uses `SystemMessagePromptTemplate.from_template(..., template_format="mustache")`
because their context strings are complex and reused across LangChain pipelines.

We use plain Python f-strings or `str.format()`. Our context assembly is a
single function that builds a markdown string -- no template reuse across
different rendering targets, no need for a template engine.

### Anthropic cache_control headers

We get cache benefits from the simpler approach: stable system prompt prefix.
Explicit `cache_control` headers are premature at our scale. Adding cache
breakpoints post-hackathon is a one-line change.

### Parallel context fetching

PostHog fetches insights in parallel because each executes a HogQL query that
can take seconds. Our context is simple DB reads: one `TutoringRelationship`,
one `Lesson`, one static schema lookup. Sequential reads complete in
single-digit milliseconds.

### XML tag wrapping

PostHog wraps context in `<attached_context>` and `<system_reminder>` XML tags
for structured LLM parsing. We use plain markdown sections (`## Current lesson`,
`## Pedagogical schema`). Markdown is clearer for our context shape (key-value
pairs and short lists) and easier to read when debugging prompts.

---

## Implementation notes

Context assembly lives in `backend/services/ai_chat/context.py`. One function
per layer, one assembler that combines them.

### Assembly pipeline

```python
from backend.models import Lesson, TutoringRelationship


class ChatContextAssembler:
    """Builds the context block for the system prompt."""

    def __init__(self, teacher_id: str, student_id: str | None, lesson_id: str | None):
        self.teacher_id = teacher_id
        self.student_id = student_id
        self.lesson_id = lesson_id

    async def build(self) -> str:
        """Assemble all context layers into a system prompt prefix."""
        sections = []

        # Layer 1+2: Subject + Student (both from TutoringRelationship)
        if self.student_id:
            relationship = await TutoringRelationship.objects.select_related(
                "student",
            ).aget(
                teacher_id=self.teacher_id,
                student_id=self.student_id,
                status="active",
            )
            subject_ctx = SubjectContext(
                subject_type=relationship.subject_type,
                subject_config=relationship.subject_config,
            )
            student_ctx = StudentContext(
                student_id=str(relationship.student_id),
                student_name=relationship.student.name,
                l1=relationship.subject_config.get("l1"),
                l2=relationship.subject_config.get("l2"),
                level=relationship.current_level,
                goal=relationship.goal,
                total_lessons=relationship.total_lessons,
                schedule_description=relationship.schedule_description,
            )
            sections.append(self._format_student_section(subject_ctx, student_ctx))

        # Layer 3: Lesson
        if self.lesson_id:
            lesson = await Lesson.objects.aget(id=self.lesson_id)
            lesson_ctx = LessonContext(
                lesson_id=str(lesson.id),
                transcript_summary=lesson.transcript_summary,
                lesson_date=lesson.date.strftime("%B %d, %Y"),
                duration_minutes=lesson.duration_minutes,
                utterance_count=len(lesson.transcript_data or []),
            )
            sections.append(self._format_lesson_section(lesson_ctx))

        # Layer 4: Pedagogical schema (static per subject_type)
        subject_type = subject_ctx.subject_type if self.student_id else "language"
        ped_ctx = get_pedagogical_context(subject_type)
        sections.append(self._format_pedagogical_section(ped_ctx))

        return "\n\n".join(sections)

    def _format_student_section(self, subject: SubjectContext, student: StudentContext) -> str:
        lang_detail = ""
        if student.l1 and student.l2:
            lang_detail = f" ({student.l1} L1 -> {student.l2} L2)"

        level_detail = ""
        if student.level:
            framework = "CEFR" if subject.subject_type == "language" else ""
            level_detail = f"- Level: {student.level}" + (f" ({framework})" if framework else "")

        lines = [
            "## Current lesson",
            f"- Subject: {subject.subject_type}{lang_detail}",
            f"- Student: {student.student_name} ({student.student_id})",
        ]
        if level_detail:
            lines.append(level_detail)
        if student.goal:
            lines.append(f"- Goal: {student.goal}")
        if student.schedule_description:
            lines.append(
                f"- Schedule: {student.schedule_description} ({student.total_lessons} lessons total)"
            )
        return "\n".join(lines)

    def _format_lesson_section(self, lesson: LessonContext) -> str:
        lines = []
        if lesson.lesson_date:
            duration = f", {lesson.duration_minutes} min" if lesson.duration_minutes else ""
            utterances = f", {lesson.utterance_count} utterances" if lesson.utterance_count else ""
            lines.append(f"- Lesson: {lesson.lesson_date}{duration}{utterances}")
        if lesson.transcript_summary:
            lines.append(f"- Summary: {lesson.transcript_summary}")
        return "\n".join(lines)

    def _format_pedagogical_section(self, ped: PedagogicalContext) -> str:
        lines = [
            "## Pedagogical schema",
            f"- Subject: {ped.subject_type}",
            f"- Error types: {', '.join(ped.error_types)}",
            f"- Severity: {', '.join(f'{s.value}' for s in ped.severity_levels)}",
        ]
        if ped.level_framework:
            lines.append(f"- Level framework: {ped.level_framework}")
        lines.append(f"- Question types: {', '.join(qt.value for qt in ped.question_types)}")
        return "\n".join(lines)


def get_pedagogical_context(subject_type: str) -> PedagogicalContext:
    """Static pedagogical schema per subject type."""
    if subject_type == "language":
        return PedagogicalContext(
            subject_type="language",
            error_types=["grammar", "vocabulary", "pronunciation", "fluency"],
            level_framework="CEFR",
        )
    # Future: math, music, etc.
    return PedagogicalContext(subject_type=subject_type)
```

### Integration with the agent loop

The agent loop calls `ChatContextAssembler.build()` once at conversation start.
The result becomes the first section of the system prompt:

```
[context block]          <-- stable prefix, cached
[mode instructions]      <-- DAILY_BRIEFING_INSTRUCTIONS or STUDENT_PRACTICE_INSTRUCTIONS
[tool descriptions]      <-- auto-generated from tool registry
---
[conversation history]   <-- varies per turn
[user message]
```

Same strategy as PostHog's `_enrich_messages()`, but simpler: one string rather
than a list of `SystemMessage` objects.

### Key differences summarized

| Aspect | PostHog | Preply Lesson Intelligence |
|--------|---------|--------------------------|
| Template engine | Mustache via LangChain | Python f-strings |
| Context source | HogQL queries, Django ORM | Django ORM (simple reads) |
| Injection point | End of system message list | Top of system prompt string |
| Fetching | Parallel with semaphore | Sequential (fast reads) |
| Caching | Explicit `cache_control` headers | Stable prefix (implicit) |
| Markup | XML tags (`<attached_context>`) | Markdown sections |
| Mixin pattern | `MaxChatMixin` mixed into LLM subclasses | `ChatContextAssembler` called by agent loop |
