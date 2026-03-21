# Tool system

> Inspired by [PostHog's Max AI assistant](https://github.com/PostHog/posthog).
> Source: [`ee/hogai/tool.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/tool.py)

## At a glance

**What this covers**: How AI chat tools work - the dual-return pattern, error handling, extensible query registry, and the boundary between skills and tools.

**Why it matters**: Tools are how teachers and students interact with lesson analysis. Every answer the AI gives comes through a tool that reads pre-computed skill output.

**Key terms**:

| Term | Meaning |
|------|---------|
| PreplyTool | Base class for all chat tools. Returns `(message, data)` |
| Dual-return | Every tool returns a message (for the AI) and data (for the frontend widget) |
| widget_type | Field in tool data that routes to a React component (e.g. `error_analysis` → ErrorAnalysisWidget) |
| SkillExecution.output_data | Where skills store results. Query tools read from here - never execute skills |
| QueryRunner | Extensible base class for query tools. Add a query = subclass + `@register_query` |
| context_prompt | Per-tool declaration of valid parameter values, injected into the system prompt |

**Prerequisites**: [skill-system.md](../skill-system.md) (how skills produce the data tools consume)

---

## What PostHog does

PostHog's `MaxTool` is the base class for every tool the Max AI assistant
can call. It wraps LangChain's `BaseTool` with four layers: dual-return
format, auto-registration, error handling, and access control.

### Dual-return: content and artifact

Every MaxTool returns a `(message, artifact)` tuple. The message feeds the
LLM's reasoning; the artifact becomes the `ui_payload` rendered in the
frontend. PostHog enforces this at the class level:

```python
# ee/hogai/tool.py
class MaxTool(AssistantContextMixin, AssistantDispatcherMixin, BaseTool):
    # LangChain's default is just "content", but we always want to return
    # the tool call artifact too - it becomes the `ui_payload`
    response_format: Literal["content_and_artifact"] = "content_and_artifact"

    async def _arun_impl(self, *args, **kwargs) -> tuple[str, Any]:
        """Tool execution, which should return a tuple of (content, artifact)"""
        raise NotImplementedError
```

This is LangChain's `response_format = "content_and_artifact"` mode. The
first element goes into the tool message content (visible to the LLM); the
second is the artifact (routed to the UI). PostHog uses a
`ToolMessagesArtifact` wrapper when the artifact contains assistant messages:

```python
class ToolMessagesArtifact(BaseModel):
    """Return messages directly. Use with `artifact`."""
    messages: Sequence[AssistantMessageUnion]
```

### Auto-registration via `__init_subclass__`

When you define a new MaxTool subclass, it registers itself into a global
dict automatically. No manual wiring:

```python
# ee/hogai/tool.py
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    if not cls.__name__.endswith("Tool"):
        raise ValueError("The name of a MaxTool subclass must end with 'Tool', for clarity")
    try:
        accepted_name = AssistantTool(cls.name)
    except ValueError:
        raise ValueError(
            f"MaxTool name '{cls.name}' is not a recognized AssistantTool value. "
            "Fix this name, or update AssistantTool in schema-assistant-messages.ts "
            "and run `pnpm schema:build`"
        )
    CONTEXTUAL_TOOL_NAME_TO_TOOL[accepted_name] = cls
```

The registry lives in [`ee/hogai/registry.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/registry.py):

```python
# ee/hogai/registry.py
CONTEXTUAL_TOOL_NAME_TO_TOOL: dict[AssistantTool, type["MaxTool"]] = {}
```

Tools are discovered by dynamically importing `max_tools` modules from
every product package. The `__init_subclass__` hook fires on import and
populates the registry.

### Error hierarchy

PostHog defines three error tiers in
[`ee/hogai/tool_errors.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/tool_errors.py).
Each carries a `retry_strategy` that tells the agent loop what to do:

```python
# ee/hogai/tool_errors.py
class MaxToolError(Exception):
    """Base exception. All errors produce tool messages visible to LLM but not end users."""

    @property
    def retry_strategy(self) -> Literal["never", "once", "adjusted"]:
        return "never"

    @property
    def retry_hint(self) -> str:
        retry_hints = {
            "never": "",
            "once": " You may retry this operation once without changes.",
            "adjusted": " You may retry with adjusted inputs.",
        }
        return retry_hints[self.retry_strategy]

class MaxToolFatalError(MaxToolError):        # "never" - permissions, missing config
    retry_strategy = "never"

class MaxToolTransientError(MaxToolError):    # "once" - rate limits, timeouts
    retry_strategy = "once"

class MaxToolRetryableError(MaxToolError):    # "adjusted" - bad inputs, fixable
    retry_strategy = "adjusted"

class MaxToolAccessDeniedError(MaxToolFatalError):
    """User lacks required permission level."""
```

The `retry_hint` property appends guidance to the error message so the LLM
knows whether to retry, adjust, or give up.

### Access control

Permission checks run before `_arun_impl`. Tools declare what they need;
the base class enforces it:

```python
# ee/hogai/tool.py
def get_required_resource_access(self) -> list[tuple[APIScopeObject, AccessControlLevel]]:
    """Declare RBAC requirements: [("insight", "editor")]"""
    return []

def _check_resource_access(self) -> None:
    required_access = self.get_required_resource_access()
    if not required_access:
        return
    for resource, required_level in required_access:
        if not self.user_access_control.check_access_level_for_resource(resource, required_level):
            raise MaxToolAccessDeniedError(resource, required_level, action="use")
```

Object-level checks are also available for checking access to specific
model instances (dashboards, insights, etc.).

### Dangerous operation approval flow

Write operations can be gated behind user approval. PostHog uses
LangGraph's `interrupt()` to pause execution mid-graph:

```python
# ee/hogai/tool.py
async def is_dangerous_operation(self, *args, **kwargs) -> bool:
    """Override to mark certain operations as requiring user approval."""
    return False

def _handle_dangerous_operation(self, preview: str | None = None, **kwargs):
    proposal_id = str(uuid.uuid4())
    serialized_payload = self._serialize_kwargs_for_storage(kwargs)

    approval_request = ApprovalRequest(
        proposal_id=proposal_id,
        tool_name=self.name,
        preview=preview,
        payload=serialized_payload,
        original_tool_call_id=self._original_tool_call_id,
    )

    # Execution pauses here. ApprovalRequest sent to frontend.
    # When resumed with Command(resume=response), interrupt() returns the response.
    response = interrupt(approval_request)
    approval_resume_payload = ApprovalResumePayload.model_validate(response)

    if approval_resume_payload.action == "approve":
        return None  # Continue with _arun_impl
    else:
        feedback = approval_resume_payload.feedback or ""
        return (
            f"The user rejected this operation with the following feedback: {feedback}. "
            "Please acknowledge their feedback and adjust your approach accordingly.",
            None,
        )
```

### Context injection into the root node

Each tool can define a `context_prompt_template` that gets formatted with
tool-specific context and injected into the root node's system message.
This steers the LLM on _when_ and _whether_ to call the tool:

```python
# ee/hogai/tool.py
context_prompt_template: str | None = None
"""Template injected into the root node's context messages.
Example: "The current filters the user is seeing are: {current_filters}."
"""
```

---

## What we take

We adapt PostHog's pattern for Preply Lesson Intelligence. The key
differences: we don't use LangChain or LangGraph (plain while-loop agent),
our tools are query-only (reading from pre-computed skill outputs), and
we target a hackathon scope.

### PreplyTool base class

Lives at `backend/services/ai_chat/tools.py`.

```python
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from backend.constants import ToolCategory, WidgetType


class PreplyTool(ABC):
    """Base class for all Preply AI tools.

    Dual-return pattern: execute() -> (message, data)
    - message: natural language summary for the LLM to reason over
    - data: structured output with widget_type for frontend rendering
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def args_schema(self) -> type[BaseModel]: ...

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.RESEARCH

    @property
    def context_prompt(self) -> str | None:
        """Optional guidance injected into system prompt when this tool is available."""
        return None

    @abstractmethod
    async def execute(self, **kwargs: Any) -> tuple[str, Any]:
        """Execute the tool.

        Returns:
            (message, data) where:
            - message: text summary for the LLM
            - data: dict with widget_type key for frontend routing, or None
        """
        ...

    def validate_args(self, **kwargs: Any) -> BaseModel:
        """Validate tool arguments against the Pydantic schema."""
        return self.args_schema(**kwargs)
```

### Widget type routing

The `data` half of the dual-return always contains a `widget_type` field.
The frontend uses it to pick the right React component:

```python
# Tool returns:
data = {
    "widget_type": WidgetType.ERROR_ANALYSIS,
    "total_errors": 9,
    "errors": [...],
}
```

```typescript
// frontend/src/components/ToolResultRenderer.tsx
const WIDGET_MAP: Record<string, React.ComponentType<WidgetProps>> = {
    [WidgetType.ERROR_ANALYSIS]: ErrorAnalysisWidget,
    [WidgetType.THEME_MAP]: ThemeMapWidget,
    [WidgetType.PRACTICE_CARD]: PracticeCardWidget,
}

function ToolResultRenderer({ data }: ToolResultProps) {
    const Widget = WIDGET_MAP[data.widget_type]
    if (!Widget) return <DefaultToolResult data={data} />
    return <Widget data={data} />
}
```

### Tool registry

PostHog uses `__init_subclass__` magic for auto-registration. We use an
explicit registry dict -- clearer for hackathon code, easier to debug:

```python
# backend/services/ai_chat/registry.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.ai_chat.tools import PreplyTool

TOOL_REGISTRY: dict[str, type["PreplyTool"]] = {}


def register_tool(cls: type["PreplyTool"]) -> type["PreplyTool"]:
    """Decorator that registers a tool class by name."""
    TOOL_REGISTRY[cls.name] = cls
    return cls


def get_tools_for_mode(mode: str) -> list[type["PreplyTool"]]:
    """Return tool classes available in a given chat mode."""
    from backend.services.ai_chat.modes import MODE_TOOLS
    return [TOOL_REGISTRY[name] for name in MODE_TOOLS[mode] if name in TOOL_REGISTRY]
```

Usage:

```python
@register_tool
class QueryErrorsTool(PreplyTool):
    name = "query_errors"
    ...
```

### Error hierarchy

Adapted from PostHog's three-tier model. Same `retry_strategy` property so
the agent loop can decide what to do:

```python
# backend/services/ai_chat/tool_errors.py
from typing import Literal


class ToolError(Exception):
    """Base exception for tool failures. Visible to LLM, not to end users."""

    @property
    def retry_strategy(self) -> Literal["never", "once", "adjusted"]:
        return "never"

    @property
    def retry_hint(self) -> str:
        hints = {
            "never": "",
            "once": " You may retry this operation once without changes.",
            "adjusted": " You may retry with adjusted inputs.",
        }
        return hints[self.retry_strategy]


class ToolFatalError(ToolError):
    """Cannot recover. Skill output missing, invalid configuration."""

    @property
    def retry_strategy(self) -> Literal["never", "once", "adjusted"]:
        return "never"


class ToolTransientError(ToolError):
    """Temporary failure. Database timeout, Classtime API rate limit."""

    @property
    def retry_strategy(self) -> Literal["never", "once", "adjusted"]:
        return "once"


class ToolRetryableError(ToolError):
    """Bad inputs the LLM can fix. Unknown student_id, invalid filter."""

    @property
    def retry_strategy(self) -> Literal["never", "once", "adjusted"]:
        return "adjusted"
```

The agent loop catches these and builds a tool message with the hint:

```python
# In the agent loop
try:
    message, data = await tool.execute(**args)
except ToolError as e:
    message = f"Error: {e}{e.retry_hint}"
    data = None
```

### Subject-aware tools

Tools receive `subject_type` from the context. A query tool reading error
analysis uses the pedagogical schema for that subject (language errors use
CEFR and grammar/vocabulary/pronunciation types; a math subject would use
different categories). The tool itself doesn't branch on subject -- the
skill outputs are already subject-aware:

```python
@register_tool
class QueryErrorsTool(PreplyTool):
    name = "query_errors"
    description = "Get errors from a student's lesson analysis. Filter by type or severity."
    args_schema = QueryErrorsArgs

    async def execute(self, student_id: str, **kwargs: Any) -> tuple[str, Any]:
        execution = await get_latest_skill_execution(
            student_id=student_id,
            skill_name="analyze-lesson-errors",
            lesson_id=kwargs.get("lesson_id"),
        )
        if not execution:
            raise ToolFatalError(f"No error analysis found for student {student_id}.")

        errors = execution.output_data["errors"]

        if error_type := kwargs.get("error_type"):
            errors = [e for e in errors if e["type"] == error_type]
        if severity := kwargs.get("severity"):
            severity_order = list(Severity)
            min_idx = severity_order.index(severity)
            errors = [e for e in errors if severity_order.index(e["severity"]) >= min_idx]

        summary = execution.output_data["summary"]
        message = (
            f"Found {len(errors)} errors"
            f"{f' ({error_type})' if error_type else ''}: "
            f"most frequent: {summary['most_frequent']}."
        )

        data = {
            "widget_type": WidgetType.ERROR_ANALYSIS,
            "student_id": student_id,
            "total_errors": len(errors),
            "errors": errors,
        }
        return message, data
```

### Context prompt injection

Like PostHog's `context_prompt_template`, each tool can optionally provide
a `context_prompt` string. The agent loop collects these from all tools
available in the current mode and appends them to the system prompt:

```python
# In system prompt builder
tool_context_lines = []
for tool_cls in get_tools_for_mode(mode):
    if tool_cls.context_prompt:
        tool_context_lines.append(tool_cls.context_prompt)

if tool_context_lines:
    system_prompt += "\n\n## Available tool guidance\n" + "\n".join(tool_context_lines)
```

## Skills vs tools: the boundary

Skills and tools live in **different repos** with a clean contract between them.

```
preply-lesson-ai-skills/              preply-lesson-intelligence/
(AI workflows, theory, CLI)           (App: backend, frontend, extension)

Skills produce output ──CLI push──>   SkillExecution.output_data
                                           ↑
                                      Query tools READ from here
                                           ↑
                                      AI chat calls query tools
```

**Hackathon flow:**
1. Worker polls `/api/v1/skill-executions/pending/`
2. Spawns `claude -p /{skill_name} {params}` (Claude Code slash command)
3. Skill reads theory + transcript → structured JSON
4. CLI pushes output → backend stores in `SkillExecution.output_data`
5. Query tools read from `output_data` - never execute skills

**How a query tool reads skill output:**
```python
async def execute(self, student_id: str, lesson_id: str | None = None, **kwargs) -> tuple[str, Any]:
    execution = await SkillExecution.objects.filter(
        skill_name="analyze-lesson-errors",
        lesson_id=lesson_id,
        status="completed",
    ).alatest("completed_at")

    errors = execution.output_data["errors"]
    # Filter, format, return
    return message, {"widget_type": "error_analysis", "errors": filtered_errors}
```

**Transition path** (post-hackathon): replace `claude -p` with Temporal activities.
Same `SkillExecution` model, same `output_data` format. Query tools don't change.

**Key principle**: query tools are pure readers. Skills can improve independently
(different repo, different iteration cycle). Testing is simple - mock
`SkillExecution.output_data`, test tool filtering.

## Tool context injection

Every tool declares valid parameter values in a `context_prompt`. All tool
context prompts are concatenated and injected into the system prompt, so the
LLM knows valid values without hallucinating.

Borrowed from Medallion's tool context pattern
([`apps/ai_chat/tools/`](https://github.com/PostHog/posthog/blob/master/ee/hogai/tool.py)).

```python
class QueryErrorsTool(PreplyTool):
    name = "query_errors"
    context_prompt = (
        "Error types: grammar, vocabulary, pronunciation, fluency (language); "
        "conceptual, procedural, calculation, notation (math). "
        "Severity levels: minor (expected at level), moderate (should be acquired), "
        "major (blocks communication)."
    )
```

Context assembly in the agent loop:
```python
tool_context = "\n".join(
    f"- {tool.name}: {tool.context_prompt}"
    for tool in available_tools
    if tool.context_prompt
)
system_prompt += f"\n\n## Available tool parameters\n{tool_context}"
```

## Extensible query registry

As query tools grow, a registry pattern prevents boilerplate. Borrowed from
Medallion's QueryRunner pattern
([`apps/ai_chat/tools/query_runner.py`](https://github.com/PostHog/posthog)).

```python
QUERY_REGISTRY: dict[str, type["PreplyQueryRunner"]] = {}

def register_query(cls):
    """Decorator: register a query class. Adding a query = subclass + @register_query."""
    QUERY_REGISTRY[cls.kind] = cls
    return cls

class PreplyQueryRunner(BaseModel, ABC):
    kind: ClassVar[str]
    widget_type: ClassVar[str | None] = None

    @abstractmethod
    async def execute(self, ...) -> tuple[str, Any]: ...

@register_query
class ErrorAnalysisQuery(PreplyQueryRunner):
    kind = "error_analysis"
    widget_type = "error_analysis"
    student_id: str
    lesson_id: str | None = None
    error_type: str | None = None
    severity: str | None = None

    async def execute(self, ...) -> tuple[str, Any]:
        execution = await get_latest_skill_execution(
            skill_name="analyze-lesson-errors",
            lesson_id=self.lesson_id,
        )
        errors = execution.output_data["errors"]
        if self.error_type:
            errors = [e for e in errors if e["type"] == self.error_type]
        message = f"Found {len(errors)} errors."
        return message, {"widget_type": self.widget_type, "errors": errors}
```

Start with 8 queries. Adding a new one = subclass + `@register_query`. No agent
loop changes needed.

| Query | Skill it reads from | Mode |
|-------|-------------------|------|
| `error_analysis` | analyze-lesson-errors | both |
| `theme_map` | analyze-lesson-themes | both |
| `level_assessment` | analyze-lesson-level | student |
| `practice_session` | generate-classtime-questions | both |
| `practice_results` | Classtime sync | both |
| `transcript_segment` | Lesson.transcript_data | student |
| `daily_overview` | prepare-daily-briefing | teacher |
| `student_report` | prepare-daily-briefing | teacher |

---

## What we skip (and why)

### LangGraph `interrupt()` approval flow

PostHog uses `interrupt()` to pause graph execution for dangerous
operations. We skip this because:

- All our MVP tools are **query-only** -- they read from `SkillExecution.output_data`.
  No writes, no side effects.
- We don't use LangGraph. Our agent is a while-loop. Implementing
  interrupt/resume adds complexity with no MVP benefit.
- If we later add write operations (e.g., "send practice to student"), we
  can add a simpler approval gate: return a confirmation widget, wait for
  user click, then execute on a second turn.

### RBAC access control

PostHog checks `UserAccessControl` with resource-level and object-level
permissions. We skip this because:

- Single-tenant hackathon. One teacher, their students.
- Role scoping (teacher vs student) is handled by **mode selection**, not
  per-tool access checks. A student in `student_practice` mode simply
  doesn't have `query_daily_overview` in their tool set.

### Billable flag

PostHog tracks whether tool-triggered LLM generations count toward
billing. We have no usage tracking or billing in the hackathon.

### `__init_subclass__` magic

PostHog's auto-registration via `__init_subclass__` is elegant but adds
indirection. For a hackathon codebase with ~7 tools, an explicit
`@register_tool` decorator is clearer:

- You can see all registrations by searching for `@register_tool`
- No need for a separate schema enum (`AssistantTool`) that must stay in
  sync with tool class names
- No dynamic module import scanning (`pkgutil.iter_modules`)

### `MaxSubtool`

PostHog has a `MaxSubtool` class for sub-operations within a tool. Our
tools are simple query runners -- no multi-step orchestration needed
within a single tool call.

---

## Implementation notes

### File layout

```
backend/services/ai_chat/
    tools.py           # PreplyTool base class
    tool_errors.py     # ToolError, ToolFatalError, ToolRetryableError, ToolTransientError
    registry.py        # TOOL_REGISTRY, register_tool, get_tools_for_mode
    modes.py           # MODE_TOOLS mapping: mode name -> list of tool names
    tools/
        query_errors.py
        query_themes.py
        query_level.py
        query_daily_overview.py
        query_student_report.py
        query_practice_results.py
        get_practice_session.py
```

### Agent loop integration

The agent loop in `backend/services/ai_chat/agent.py` drives tool
execution:

1. LLM returns a tool call with name + args
2. Look up tool class in `TOOL_REGISTRY`
3. Validate args with `tool.validate_args(**raw_args)`
4. Call `tool.execute(**validated_args)`
5. Catch `ToolError` subtypes, build error message with `retry_hint`
6. Stream `TOOL_START` / `TOOL_RESULT` SSE events
7. Feed `(message, data)` back into the LLM as a tool result

```python
async def run_tool(tool_name: str, raw_args: dict) -> tuple[str, Any]:
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if not tool_cls:
        return f"Unknown tool: {tool_name}", None

    tool = tool_cls()
    try:
        validated = tool.validate_args(**raw_args)
        message, data = await tool.execute(**validated.model_dump())
    except ToolError as e:
        message = f"Error: {e}{e.retry_hint}"
        data = None

    return message, data
```

### Adding a new tool

1. Create `backend/services/ai_chat/tools/query_foo.py`
2. Define args schema, implement `execute()`, return `(message, data)`
3. Decorate with `@register_tool`
4. Add the tool name to the relevant mode in `modes.py`
5. If it returns widget data, add the `WidgetType` to constants and build
   the frontend component

```python
# backend/services/ai_chat/tools/query_foo.py
from pydantic import BaseModel, Field

from backend.services.ai_chat.tools import PreplyTool
from backend.services.ai_chat.registry import register_tool
from backend.services.ai_chat.tool_errors import ToolFatalError


class QueryFooArgs(BaseModel):
    student_id: str = Field(description="Student to query")


@register_tool
class QueryFooTool(PreplyTool):
    name = "query_foo"
    description = "Get foo data for a student."
    args_schema = QueryFooArgs

    async def execute(self, student_id: str, **kwargs) -> tuple[str, Any]:
        execution = await get_latest_skill_execution(
            student_id=student_id,
            skill_name="analyze-foo",
        )
        if not execution:
            raise ToolFatalError(f"No foo analysis found for student {student_id}.")

        message = f"Found foo data for {student_id}."
        data = {
            "widget_type": WidgetType.FOO,
            "student_id": student_id,
            "results": execution.output_data,
        }
        return message, data
```

### Testing tools

Test the `execute()` method directly. Mock `get_latest_skill_execution`
to return fixture data. Verify both halves of the dual-return:

```python
async def test_query_errors_filters_by_severity():
    tool = QueryErrorsTool()
    message, data = await tool.execute(student_id="s1", severity="moderate")

    assert "Found" in message
    assert data["widget_type"] == WidgetType.ERROR_ANALYSIS
    assert all(e["severity"] in ("moderate", "major") for e in data["errors"])


async def test_query_errors_missing_execution_raises_fatal():
    tool = QueryErrorsTool()
    with pytest.raises(ToolFatalError):
        await tool.execute(student_id="nonexistent")
```

### Key differences from PostHog, summarized

| Aspect | PostHog MaxTool | Preply PreplyTool |
|--------|----------------|-------------------|
| Framework | LangChain `BaseTool` + LangGraph | Plain Python ABC |
| Registration | `__init_subclass__` magic | `@register_tool` decorator |
| Dual-return | `response_format = "content_and_artifact"` | `execute() -> (message, data)` |
| Error hierarchy | `MaxToolError` with `retry_strategy` | `ToolError` with `retry_strategy` (same pattern) |
| Access control | RBAC with `UserAccessControl` | Mode-based tool filtering |
| Approval flow | LangGraph `interrupt()` | Not needed (query-only tools) |
| Context injection | `context_prompt_template` with formatting | `context_prompt` string property |
| Billing | `billable` flag | Not needed |
