# Trust and transparency

> Inspired by [PostHog's Max AI](https://github.com/PostHog/posthog) and Medallion's tier-2 planning & transparency patterns.
> Core principle: **Users trust AI when they can see its reasoning, verify its sources, and understand its limitations.**

## At a glance

**What this covers**: The trust stack that makes AI transparent - progressive disclosure, reasoning anchors, ProcessTimeline visualization, and the approval flow for write operations.

**Why it matters**: Teachers perceive AI lesson analysis as surveillance unless they can see the AI's work. Transparency converts suspicion into trust.

**Key terms**:

| Term | Meaning |
|------|---------|
| Trust stack | Four layers: WHY (reasoning) → WHAT (data accessed) → WHERE (source data) → HOW (answer derivation) |
| Progressive disclosure | Summary visible, details expandable. Level 1: status. Level 2: tool step. Level 3: full widget |
| ProcessTimeline | React component showing thinking blocks, tool calls, and status steps in a unified timeline |
| Reasoning field | Every skill output includes `reasoning` explaining what framework was applied and why |
| Approval flow | Write operations (Classtime sessions) require teacher review before sending to students |
| ThinkingIndicator | Shows accumulated ✓ completed steps and → current step during AI processing |

**Prerequisites**: [streaming.md](06-streaming.md), [tool-system.md](03-tool-system.md)

---

Preply's Lesson Insights faces a specific trust problem: teachers perceive
AI analysis of their lessons as surveillance. The antidote is transparency --
showing the AI's work at every step so the teacher understands what happened,
why, and from what evidence.

This document defines the trust stack, maps it to SSE events and frontend
components, and specifies the implementation patterns adapted from PostHog
and Medallion for our system.

---

## The trust stack

Four layers, each building on the previous. Each layer maps to an SSE event
type, a frontend rendering pattern, and a user experience.

### Layer 1: WHY -- show AI reasoning

**SSE event**: `THINKING`
**Frontend**: collapsible reasoning block
**User sees**: the framework the AI applied and why

The AI emits reasoning before and during tool calls. This isn't "thinking
out loud" -- it's structured disclosure of which pedagogical framework was
applied and what evidence was considered.

```
event: thinking
data: {"content": "Pulling Maria's report: errors from analyze-lesson-errors skill, practice results from Classtime, suggested focus based on CEFR B1 descriptors."}
```

Frontend renders as a collapsible block, collapsed by default:

```
▸ Reasoning: Pulling Maria's report: errors, practice results, suggested focus
```

Expanded:

```
▾ Reasoning
  Pulling Maria's report: errors from analyze-lesson-errors skill,
  practice results from Classtime, suggested focus based on CEFR B1
  descriptors.
```

### Layer 2: WHAT -- show what data is being accessed

**SSE event**: `TOOL_START`
**Frontend**: expandable step with tool name and parameters
**User sees**: which tool was called, with what inputs

Every tool call is visible. The user knows what data the AI is accessing
before the result arrives.

```
event: tool_start
data: {"tool": "query_errors", "args": {"student_id": "maria_42", "severity": "moderate"}}
```

Frontend renders as a step indicator:

```
→ query_errors (student: Maria Garcia, severity: moderate+)
```

### Layer 3: WHERE -- show the source data

**SSE event**: `TOOL_RESULT`
**Frontend**: widget with actual data and source attribution
**User sees**: the raw findings, linked back to transcript positions

Tool results render as interactive widgets, not raw JSON. Each data point
links back to its source (transcript position, lesson date, skill execution).

```
event: tool_result
data: {"message": "Found 9 errors (4 grammar, 3 vocab, 2 pronunciation).", "data": {"widget_type": "error_analysis", "total_errors": 9, "errors": [...]}}
```

Frontend renders as the appropriate widget (ErrorAnalysisWidget,
ThemeMapWidget, etc.) with expandable details and source links.

### Layer 4: HOW -- show the answer derivation

**SSE event**: `STREAM`
**Frontend**: streaming text that references specific data points
**User sees**: the AI's commentary connecting findings to recommendations

The AI's final response references specific data from the widgets.
Not generic advice -- grounded commentary that the teacher can verify
against the displayed data.

```
event: stream
data: {"content": "Past tense errors are the priority -- they appeared 3 times at 12:45, 18:20, and 24:10, and Maria's practice scores confirm she needs more work on sentence-level application (sorter: 0/2)."}
```

### Complete event flow

A single teacher question produces this sequence:

```
User: "How did Maria do?"

SSE event sequence:
1. STATUS    → "Looking up Maria's report..."
2. THINKING  → "Querying student report: errors, practice results, suggested focus."
3. TOOL_START → query_student_report(student_id: "maria_42")
4. TOOL_RESULT → {widget_type: "error_analysis", errors: [...], ...}
5. STREAM    → "Maria had 9 errors in her last lesson..."
6. STREAM    → " The past tense pattern is most significant..."
7. STREAM    → " Practice score: 75% -- strong on conjugation, weak on word order."
8. COMPLETE  → {}
```

Frontend renders each event as it arrives:

| SSE event | Frontend component | Trust layer |
|-----------|-------------------|-------------|
| `STATUS` | Status bar text | Progress |
| `THINKING` | `<CollapsibleReasoning>` | WHY |
| `TOOL_START` | `<ToolStep>` with name + params | WHAT |
| `TOOL_RESULT` | Widget (ErrorAnalysis, ThemeMap, etc.) | WHERE |
| `STREAM` | Streaming text block | HOW |
| `COMPLETE` | Stop indicator | Done |

---

## Progressive disclosure

Summary visible, details expandable. Three levels of information density,
each accessible from the previous.

### Level 1: one-line status

Minimal, non-intrusive. Shows that work is happening.

```
→ Analyzing errors for Alex...
```

Maps to `STATUS` events. Replaced on each update -- no accumulation.

### Level 2: tool execution step

Shows what the AI did and the headline result.

```
✓ query_errors → 9 errors found, most frequent: grammar
```

Maps to `TOOL_START` (arrow indicator) → `TOOL_RESULT` (checkmark + summary).
Expandable to reveal parameters:

```
✓ query_errors (student: Alex Chen, severity: moderate+) → 9 errors
```

### Level 3: full widget

Interactive component with all data, grouping, severity badges,
and source links.

Each widget follows the same anatomy:

```
┌─ [Header: widget type + count] ─────────────┐
│ [Summary stat: most important number]        │
│ [Distribution: breakdown by category]        │
│                                              │
│ ▾ [Expandable group 1]                       │
│   [Detail item with severity badge]          │
│   [Source link → transcript position]        │
│   [Reasoning block → collapsible]            │
│                                              │
│ ▸ [Collapsed group 2]                        │
│ ▸ [Collapsed group 3]                        │
└──────────────────────────────────────────────┘
```

### Widget examples

**ErrorAnalysisWidget** -- errors grouped by type with severity badges:

```
┌─ Error analysis ─────────────────────────────┐
│ 9 errors found                               │
│ ■ Grammar (4)  ■ Vocabulary (3)  ■ Pron (2) │
│                                               │
│ ▾ Grammar errors                             │
│   ● moderate  "I go yesterday" → "I went..." │
│     Past simple required for completed action │
│     12:45 [▸ view in transcript]             │
│     [▸ reasoning: B1 should know past simple]│
│                                               │
│ ▸ Vocabulary errors (3)                      │
│ ▸ Pronunciation errors (2)                   │
└───────────────────────────────────────────────┘
```

**ThemeMapWidget** -- topic clusters with vocabulary:

```
┌─ Lesson themes ──────────────────────────────┐
│ 3 themes identified                          │
│                                               │
│ ▾ Travel planning (42 utterances)            │
│   airport, boarding pass, gate, departure,   │
│   arrival, luggage, terminal                 │
│   [▸ see in transcript: 2:00 - 18:30]       │
│                                               │
│ ▸ Restaurant vocabulary (31 utterances)      │
│ ▸ Giving directions (24 utterances)          │
└───────────────────────────────────────────────┘
```

**PracticeCardWidget** -- session preview with source errors:

```
┌─ Practice: past tense ───────────────────────┐
│ 8 exercises generated                        │
│ 3× fill-in-gap  2× sorter  2× MC  1× cloze │
│                                               │
│ Source errors:                                │
│   • 12:45 "I go yesterday"                   │
│   • 24:10 "She walk to school last week"     │
│                                               │
│ [Preview questions]  [Open in Classtime]      │
└───────────────────────────────────────────────┘
```

**ScheduleWidget** -- daily briefing overview:

```
┌─ Today's lessons ────────────────────────────┐
│ 5 students                                   │
│ 3 completed practice  │  1 not started ⚠     │
│                                               │
│ ▾ Maria Garcia (B1, 10:00)                   │
│   Practice: 75%  │  Errors: 9  │  Focus: ⚠  │
│   Suggested: past tense in narratives        │
│                                               │
│ ▸ Alex Chen (A2, 11:00) ✓                    │
│ ▸ Yuki Tanaka (B2, 13:00) ✗ not started     │
│ ▸ Pierre Dubois (B1, 14:00) ⚠               │
│ ▸ Ana Silva (A2, 15:00) - first lesson       │
└───────────────────────────────────────────────┘
```

Every widget shares three properties:
1. **Header** with type label and primary count
2. **Summary stat** visible without expanding anything
3. **Expandable detail** with source links back to transcript or skill output

---

## Thinking indicator with step trail

A spinner is not transparency. The thinking indicator accumulates completed
steps, showing progress as a trail -- not replacing one status line with
another.

### Pattern (from Medallion's ThinkingIndicator)

```
✓ Loaded student context (Alex Chen, B1)
✓ Queried lesson errors (9 found)
→ Filtering by severity...
```

Each line corresponds to a completed or in-progress step. Completed steps
stay visible. The current step shows an arrow indicator.

### Implementation

The frontend maintains a list of thinking steps, driven by `STATUS` and
`THINKING` events:

```typescript
interface ThinkingStep {
    id: string
    message: string
    status: 'pending' | 'active' | 'complete'
    timestamp: number
}

interface ThinkingIndicatorProps {
    steps: ThinkingStep[]
}

function ThinkingIndicator({ steps }: ThinkingIndicatorProps) {
    return (
        <div className="thinking-trail">
            {steps.map(step => (
                <div key={step.id} className="thinking-step">
                    <span className="step-icon">
                        {step.status === 'complete' ? '✓' :
                         step.status === 'active' ? '→' : '○'}
                    </span>
                    <span className="step-text">{step.message}</span>
                </div>
            ))}
        </div>
    )
}
```

### Event mapping

| SSE event | Step trail action |
|-----------|------------------|
| `STATUS` | Add new step as `active`, mark previous as `complete` |
| `THINKING` | Add reasoning step (rendered differently -- italic, collapsible) |
| `TOOL_START` | Add tool step as `active` |
| `TOOL_RESULT` | Mark tool step as `complete`, append summary |
| `COMPLETE` | Mark all remaining steps as `complete` |

### Collapsing on completion

When the full response is rendered, the step trail collapses into a single
summary line:

```
▸ 3 steps completed (query_student_report, query_errors, query_themes)
```

Expandable to show the full trail. This prevents the chat from becoming
cluttered with step trails from previous turns while keeping them
accessible.

## ProcessTimeline: unified step visualization

Borrowed from Medallion's `ProcessTimeline.tsx`. A single component
orchestrates all agent activity into a coherent timeline.

Three step types rendered in sequence:

| Step type | Trigger | Renders as |
|-----------|---------|-----------|
| `thinking` | THINKING event | Collapsible reasoning block with markdown |
| `tool_call` | TOOL_START event | Tool name + status badge + embedded widget |
| `status` | STATUS event | One-line status with spinner or checkmark |

**Timeline for a typical query_errors call:**
```
✓ Loaded context for Alex Chen (B1, Chinese → English)     [thinking]
✓ query_errors: 9 errors found                              [tool_call]
  └── ErrorAnalysisWidget                                   [widget]
     Grammar: 4 | Vocabulary: 3 | Pronunciation: 2
→ Composing response...                                     [status]
```

The timeline collapses to a one-line summary when the agent's turn completes:
```
▶ Analyzed 9 errors for Alex Chen (3 tools used)            [collapsed]
```

This maps directly to our trust stack:
- **WHY**: thinking block shows reasoning
- **WHAT**: tool_call shows data access
- **WHERE**: widget shows source data
- **HOW**: AI response references specific findings

---

## Tool execution visibility

Every tool call is visible to the user. This is non-negotiable -- invisible
tool calls erode trust.

### Display sequence

1. **TOOL_START**: tool name and human-readable description of inputs

   ```
   → Querying errors for today's lesson...
     query_errors(student: Maria Garcia, severity: moderate+)
   ```

2. **TOOL_RESULT**: widget appears with structured data

   The widget replaces the "loading" state of the tool step.
   The step indicator updates to show completion:

   ```
   ✓ query_errors → 9 errors (4 grammar, 3 vocabulary, 2 pronunciation)
   ```

3. **AI commentary**: references specific data points from the widget

   The streaming text that follows references concrete numbers and
   findings from the tool result, so the teacher can cross-reference.

### Tool display format

Different tools render their results differently. The `widget_type` field
in the tool result payload determines which React component renders:

```typescript
const WIDGET_MAP: Record<string, React.ComponentType<WidgetProps>> = {
    [WidgetType.ERROR_ANALYSIS]: ErrorAnalysisWidget,   // Table with severity badges
    [WidgetType.THEME_MAP]: ThemeMapWidget,              // Collapsible topic cards
    [WidgetType.PRACTICE_CARD]: PracticeCardWidget,      // Session preview + actions
}

function ToolResultRenderer({ data }: ToolResultProps) {
    const Widget = WIDGET_MAP[data.widget_type]
    if (!Widget) return <DefaultToolResult data={data} />
    return <Widget data={data} />
}
```

Tools without a dedicated widget fall through to `DefaultToolResult`,
which renders a formatted key-value display rather than raw JSON.

### SSE event sequence for a typical query_errors call

```
id: 3
event: thinking
data: {"content": "Looking at Maria's errors from the latest lesson, filtering for moderate+ severity to focus on the most impactful patterns."}

id: 4
event: tool_start
data: {"tool": "query_errors", "args": {"student_id": "maria_42", "lesson_id": null, "severity": "moderate"}}

id: 5
event: tool_result
data: {
  "message": "Found 9 errors (4 grammar, 3 vocabulary, 2 pronunciation). Most frequent: grammar.",
  "data": {
    "widget_type": "error_analysis",
    "student_id": "maria_42",
    "total_errors": 9,
    "errors": [
      {
        "type": "grammar",
        "severity": "moderate",
        "original": "I go to the store yesterday",
        "corrected": "I went to the store yesterday",
        "explanation": "Past simple required for completed past action",
        "transcript_position": {"utterance": 34, "timestamp": "12:45"},
        "reasoning": "Error taxonomy: morphological > verb tense. B1 should have acquired past simple. Marked moderate."
      }
    ]
  }
}

id: 6
event: stream
data: {"content": "Maria had 4 grammar errors in her last lesson. The most significant pattern is past tense -- she said \"I go yesterday\" at 12:45, \"She walk last week\" at 24:10, and \"They are come\" at 31:55. These are moderate severity because B1 learners should have acquired past simple."}
```

---

## Message merging by ID

PostHog's pattern: messages can be updated in-place, not just appended.
This prevents the chat from filling with duplicate or stale content during
streaming and tool execution.

### The problem with append-only

Without merging:
- Streaming text creates a new message for every chunk
- Tool results appear as separate messages below "loading" placeholders
- Thinking blocks remain expanded after completion
- Reconnection replays produce duplicates

### PostHog's add_and_merge_messages()

PostHog solves this with a merge-by-ID reducer on the message state.
Every message has a stable `id`. When a new message arrives with the same
ID as an existing one, it replaces the existing message rather than
appending.

From [`ee/hogai/utils/types/base.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/utils/types/base.py):

```python
def add_and_merge_messages(
    left_value: Sequence[AssistantMessageUnion],
    right_value: Sequence[AssistantMessageUnion],
) -> Sequence[AssistantMessageUnion]:
    """Merges two lists of messages, updating existing messages by ID.

    By default, this ensures the state is "append-only", unless the
    new message has the same ID as an existing message.
    """
    left = list(left_value)
    right = list(right_value)

    # Assign missing IDs
    for m in left:
        if m.id is None:
            m.id = str(uuid.uuid4())
    for m in right:
        if m.id is None:
            m.id = str(uuid.uuid4())

    if isinstance(right_value, ReplaceMessages):
        return right

    left_idx_by_id = {m.id: i for i, m in enumerate(left)}
    merged = left.copy()
    for m in right:
        if (existing_idx := left_idx_by_id.get(m.id)) is not None:
            merged[existing_idx] = m
        else:
            merged.append(m)
    return merged
```

### Our adaptation

We apply the same pattern but without LangGraph state management. The
frontend message reducer handles merging:

```typescript
// frontend/src/lib/sse.ts

function mergeMessages(
    existing: Message[],
    incoming: Message
): Message[] {
    const idx = existing.findIndex(m => m.id === incoming.id)
    if (idx >= 0) {
        // Replace in-place
        return existing.map((m, i) => i === idx ? incoming : m)
    }
    // Append
    return [...existing, incoming]
}
```

### What gets merged

| Scenario | Behavior |
|----------|----------|
| Streaming text chunks | Same message ID, content grows with each chunk |
| Tool result arrives | Replaces the "loading" placeholder that shares its ID |
| Thinking block completes | Same ID, `status` field changes from `active` to `complete` |
| Reconnection replay | Already-seen IDs are updated, not duplicated |

### Backend support

SSE events carry a `message_id` field when they contribute to a mergeable
message:

```python
class StreamEvent(BaseModel):
    type: StreamEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    message_id: str | None = None  # Stable ID for merge-by-ID updates
```

The agent loop assigns a stable `message_id` at the start of each
assistant turn and reuses it across all `STREAM` events for that turn.
`TOOL_RESULT` events get their own `message_id` (one per tool call).

---

## Reasoning field as trust anchor

Every skill output includes a `reasoning` field that explains what
framework was applied and why. This is the content that powers `THINKING`
events -- it isn't improvised by the chat LLM, it comes from the
analysis skill that produced the data.

### What the reasoning field contains

Three components:
1. **Framework applied**: which taxonomy, which CEFR descriptor, which
   severity criteria
2. **Why this categorization**: the specific evidence that led to this
   classification, not just the label
3. **What was considered and ruled out**: alternative interpretations
   the AI evaluated and rejected

### Example

```json
{
  "type": "grammar",
  "severity": "moderate",
  "original": "I go to the store yesterday",
  "corrected": "I went to the store yesterday",
  "explanation": "Past simple required for completed past action",
  "reasoning": "Error taxonomy: morphological > verb tense. B1 should have acquired past simple (CEFR B1 descriptor: 'can narrate past events using appropriate tenses'). Marked moderate because it blocks narrative coherence but not basic communication. Considered minor (could be L1 transfer from Spanish present-for-past) but frequency (3 occurrences) indicates systematic gap, not slip.",
  "position": {"utterance": 34, "timestamp": "12:45"}
}
```

### Why this matters

Generic AI assistants say: "You made a grammar error."
Our system says: "Error taxonomy: morphological > verb tense. B1 should
have acquired past simple. Marked moderate because it blocks narrative
coherence."

The teacher can evaluate whether the categorization is correct. The
student can understand not just what was wrong but why it matters at
their level. The reasoning is verifiable against the transcript position.

This is our unique advantage over generic AI tools: pedagogically grounded
reasoning that follows established frameworks (CEFR, error taxonomy),
not pattern matching on surface forms.

### How reasoning flows through the system

```
Skill execution (background)
  → analyze-lesson-errors produces errors with reasoning field
  → Stored in SkillExecution.output_data

Agent loop (conversation)
  → query_errors tool reads from output_data
  → THINKING event emits a summary of the reasoning
  → TOOL_RESULT delivers the full data including reasoning per error
  → STREAM references specific reasoning points in commentary

Frontend
  → ThinkingIndicator shows the summary reasoning
  → ErrorAnalysisWidget shows per-error reasoning as collapsible blocks
  → AI text references reasoning: "Marked moderate because..."
```

---

## Error transparency

Three error types, three UX responses. The principle: never hide errors,
always explain what happened and what the user can do about it.

### Fatal errors

Something is fundamentally broken. The system cannot proceed.

**User sees**:
```
I can't access lesson data right now. This usually means the
connection to the server is interrupted.

[Retry connection]
```

**Characteristics**:
- Clear statement of what failed (not "something went wrong")
- Actionable next step (retry button, not just a message)
- No technical jargon (not "500 Internal Server Error")

**SSE implementation**: connection drops, `EventSource.onerror` fires.
Frontend shows the error inline in the chat with a retry action.

### Retryable errors

A tool call failed but the system can try a different approach.

**User sees**:
```
✓ Loaded student context (Alex Chen, B1)
✗ Queried lesson errors - data temporarily unavailable
→ Trying a different approach...
```

**Characteristics**:
- The failed step is visible (not hidden)
- The retry is visible ("Trying a different approach...")
- If the retry succeeds, the flow continues normally
- If the retry also fails, escalates to a clear error message

**SSE implementation**: the agent loop catches the tool error, emits a
`STATUS` event with the retry message, and tries an alternative tool or
query strategy. The step trail shows the failure and retry.

### Transient errors

Brief hiccups that resolve themselves. Network blip, slow response.

**User sees**:
```
→ Taking a moment...
```

Then the response continues normally.

**Characteristics**:
- Minimal disruption (one-line status update)
- Auto-recovers without user action
- No error styling (no red, no warning icons)
- If it persists beyond a threshold (e.g., 30 seconds), escalates to
  retryable or fatal

**SSE implementation**: `EventSource` handles reconnection automatically.
The frontend shows "Reconnecting..." during the gap, then resumes
streaming. `Last-Event-ID` ensures no events are lost.

### Error rendering rules

| Error type | Color | Icon | Action | Auto-dismiss |
|------------|-------|------|--------|-------------|
| Fatal | Red border | Error icon | Retry button | No |
| Retryable | Amber text | Warning icon | Auto-retry visible | Yes, on success |
| Transient | Gray text | None | None | Yes, after 3s |

---

## What we take from Medallion

Medallion's tier-2 planning & transparency document defines patterns for
making agent reasoning visible. We adopt six patterns:

### Trust stack (WHY, WHAT, WHERE, HOW)

Medallion layers information disclosure: first show reasoning, then tool
calls, then data, then synthesis. We map this directly to our SSE event
types. The layering ensures the user can verify at any depth without
being overwhelmed at the surface level.

### Progressive disclosure (summary, steps, full widget)

Three information densities, each expandable from the previous. Medallion
uses collapsible tool results and step trails. We extend this to widgets
with consistent anatomy (header, summary stat, expandable detail, source
link).

### Thinking indicator with step trail

Medallion's `ThinkingIndicator` component accumulates completed steps
rather than replacing a single status line. We adopt this pattern for our
`ThinkingIndicator.tsx` component, with the addition of reasoning blocks
from `THINKING` events.

### Tool execution visibility

Every tool call is visible in Medallion's UI: `TOOL_START` shows the call,
`TOOL_RESULT` shows the result. We add display format metadata
(`widget_type`) so different tools render differently rather than showing
raw JSON.

### Error transparency

Medallion categorizes errors into fatal, retryable, and transient with
distinct UX for each. We adopt this three-tier model and map it to our
SSE reconnection and agent loop error handling.

### Message merging for streaming

Medallion's tier-2 document specifies message merging by ID, adapted from
PostHog's `add_and_merge_messages()`. We implement the same pattern in
our frontend message reducer and SSE event format.

---

## What we add (unique to Preply)

Our trust model goes beyond generic AI transparency. Four additions
specific to educational AI:

### Pedagogical reasoning

Every error categorization is grounded in established frameworks: CEFR
descriptors for language level, linguistic error taxonomy for error types,
severity criteria based on communicative impact. The `reasoning` field
isn't AI commentary -- it's framework application that a teacher can
evaluate.

A generic AI might say "grammar error." Our system says "morphological >
verb tense, B1 should have acquired this, moderate because it blocks
narrative coherence." The teacher can agree or disagree with the
categorization.

### Source linking to transcript positions

Every finding links to a specific position in the lesson transcript:
utterance number and timestamp. The teacher or student can verify any
claim against the original lesson moment. This is source attribution
at the granularity of individual utterances, not just "based on your
lesson."

```typescript
interface TranscriptPosition {
    utterance: number
    timestamp: string  // "12:45"
}
```

Clicking a source link in a widget scrolls to that position in the
transcript viewer (when available in the side panel).

### Teacher-student context awareness

The AI knows the tutoring relationship. For the same error data:

- **Teacher sees**: severity assessment, comparison to expected level,
  teaching suggestions, practice completion data
- **Student sees**: encouraging explanation, the underlying rule,
  examples at their level, link to practice exercises

Same data, different framing. The `mode` (daily_briefing vs
student_practice) determines how findings are presented, and the context
injection (StudentContext, PedagogicalContext) grounds the AI's language
in the specific tutoring relationship.

### Subject-aware error taxonomy

Different subjects produce different error types. The system communicates
these differences clearly:

- **Language**: grammar, vocabulary, pronunciation, fluency (with CEFR
  grounding)
- **Math** (future): conceptual, procedural, notation, reasoning
- **Music** (future): rhythm, pitch, technique, theory

The `PedagogicalContext.error_types` field is dynamic per subject type.
Widgets adapt their grouping and severity criteria accordingly. The trust
model works across subjects because the reasoning framework is always
explicit.

---

## Approval UX for write operations

Creating Classtime sessions sends practice to students - a write operation
that deserves teacher review. Borrowed from Medallion's approval flow.

**Flow:**
1. AI calls `create_classtime_session` tool
2. Tool detects `requires_approval = True`
3. Backend emits APPROVAL SSE event with preview:
   - Question count and types
   - Focus topic
   - Sample questions (first 3)
   - Target student(s)
4. Frontend shows ApprovalDialog
5. Teacher reviews → "Send to student" or "Edit first"
6. On approve: tool executes, session created on Classtime
7. On deny: AI acknowledges, suggests adjustments

**Why this matters for trust:**
- Teacher sees exactly what goes to students
- No surprise content in student practice
- Teacher remains in control of the pedagogical loop
- Builds confidence in the system's judgment

**What triggers approval:**
- `create_classtime_session` (sends practice to students)

**What does NOT need approval** (read-only query tools):
- `query_errors`, `query_themes`, `query_level` - just reading
- `query_practice_results` - just reading
- `get_transcript_segment` - just reading

---

## Implementation checklist

Files and what they implement. Ordered by dependency.

### Backend

| File | Purpose |
|------|---------|
| `backend/stream/events.py` | SSE event types (`STATUS`, `THINKING`, `TOOL_START`, `TOOL_RESULT`, `STREAM`, `COMPLETE`), `message_id` field, payload schemas |
| `backend/services/ai_chat/agent.py` | Emit trust events during agent loop: `THINKING` before tool calls, `TOOL_START`/`TOOL_RESULT` around execution, `STATUS` for progress |
| `backend/services/skills/` | Ensure all skill outputs include `reasoning` field per error/theme/assessment |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/lib/sse.ts` | EventSource consumer with message merging by ID, reconnection via `Last-Event-ID` |
| `frontend/src/components/ThinkingIndicator.tsx` | Step trail component: accumulates completed steps, shows current step, collapses on completion |
| `frontend/src/components/widgets/ErrorAnalysisWidget.tsx` | Error table with severity badges, expandable reasoning, transcript position links |
| `frontend/src/components/widgets/ThemeMapWidget.tsx` | Topic clusters with vocabulary lists, transcript range links |
| `frontend/src/components/widgets/PracticeCardWidget.tsx` | Session preview with source errors, action buttons |
| `frontend/src/components/widgets/ScheduleWidget.tsx` | Daily briefing overview with per-student status |
| `frontend/src/components/CollapsibleReasoning.tsx` | Reusable collapsible block for reasoning text, used by ThinkingIndicator and widgets |
| `frontend/src/components/ToolStep.tsx` | Single tool execution step: pending → active → complete states |

### Shared

| File | Purpose |
|------|---------|
| `backend/constants.py` | `StreamEventType` enum shared with frontend |
| `frontend/src/lib/constants.ts` | `StreamEventType`, `WidgetType` mirror of backend constants |
