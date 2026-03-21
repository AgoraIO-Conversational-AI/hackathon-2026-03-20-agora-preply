# Frontend UX

> Inspired by [PostHog's Max AI](https://github.com/PostHog/posthog) and Medallion's frontend UX patterns.
> Source: PostHog [`ee/hogai/utils/types/`](https://github.com/PostHog/posthog/blob/master/ee/hogai/utils/types/)

## At a glance

**What this covers**: React components for the Chrome extension chat UI - widgets, modes, loading states, suggested chips, ProcessTimeline, and ApprovalDialog.

**Why it matters**: The frontend is what teachers and students actually see. Good UX makes AI insights accessible; bad UX makes them confusing.

**Key terms**:

| Term | Meaning |
|------|---------|
| Widget | React component rendering tool results (ErrorAnalysisWidget, ThemeMapWidget, PracticeCardWidget, ScheduleWidget) |
| widget_type | Field in tool data that routes to the correct widget via a registry |
| Mode-based UI | `daily_briefing` and `student_practice` each have different greetings, tools, and suggested chips |
| ProcessTimeline | Unified timeline of thinking blocks, tool calls, and status steps |
| Suggested chips | Context-aware action buttons that appear after each AI response |
| Message merging | Frontend updates messages by ID instead of appending (upsertMessage pattern) |
| ApprovalDialog | Modal for teacher to review Classtime session before sending to students |

**Prerequisites**: [streaming.md](06-streaming.md), [trust-and-transparency.md](07-trust-and-transparency.md)

**See also**: [visual-design-system.md](09-visual-design-system.md) for colors, typography, spacing, animation, and accessibility rules.

---

How the Chrome extension side panel renders AI chat interactions.
See [conversational-ux.md](../conversational-ux.md) for tools and the
dual-return pattern. See [streaming.md](06-streaming.md) for SSE events.

---

## Widget system

Every tool returns `(message, data)`. The `data` dict carries a
`widget_type` field that routes to a React component via a registry:

```typescript
// frontend/src/components/widgets/ToolResultRenderer.tsx
const WIDGET_MAP: Record<string, React.ComponentType<WidgetProps>> = {
    [WidgetType.ERROR_ANALYSIS]: ErrorAnalysisWidget,
    [WidgetType.THEME_MAP]: ThemeMapWidget,
    [WidgetType.PRACTICE_CARD]: PracticeCardWidget,
    [WidgetType.SCHEDULE]: ScheduleWidget,
}

function ToolResultRenderer({ data }: { data: ToolResultData }) {
    const Widget = WIDGET_MAP[data.widget_type]
    if (!Widget) return <DefaultToolResult data={data} />
    return <Widget data={data} />
}
```

Flat registry. Adding a widget = one `WIDGET_MAP` entry + one component file.

### ErrorAnalysisWidget

Primary widget for both modes. Renders `analyze-lesson-errors` output.

```typescript
interface ErrorItem {
    type: 'grammar' | 'vocabulary' | 'pronunciation' | 'fluency'
    severity: 'minor' | 'moderate' | 'major'
    original: string
    corrected: string
    explanation: string
    reasoning: string
    transcript_position: { utterance: number; timestamp: string }
}

interface ErrorAnalysisData {
    widget_type: 'error_analysis'
    student_id: string
    total_errors: number
    errors_by_type: Record<string, number>
    errors: ErrorItem[]
}
```

- **Header**: `"{total_errors} errors found"` with type chips: `grammar (4)`, `vocabulary (3)`
- **Body**: Errors grouped by `type`, each group collapsible
- **Each error**: severity badge (`minor`=gray, `moderate`=amber, `major`=red),
  `original` strikethrough -> `corrected` in green, `explanation` inline
- **Expand**: `reasoning` field + transcript position link (`"{timestamp} - view in transcript"`)

### ThemeMapWidget

Renders `analyze-lesson-themes` output as collapsible topic cards.

```typescript
interface ThemeMapData {
    widget_type: 'theme_map'
    student_id: string
    themes: Array<{
        topic: string
        vocabulary: string[]
        utterance_count: number
        transcript_range: { start: string; end: string }
    }>
}
```

- **Header**: `"{themes.length} themes covered"`
- **Collapsed**: Topic name + `"({utterance_count} utterances)"`
- **Expanded**: Full `vocabulary` list as tags, transcript range link

### PracticeCardWidget

Classtime session preview or completion status.

```typescript
interface PracticeCardData {
    widget_type: 'practice_card'
    student_id: string
    question_count: number
    question_types: Record<string, number>  // {GAP: 3, SORTER: 2}
    focus_topic: string
    source_errors: Array<{ timestamp: string; original: string }>
    session_url: string | null
    session_code: string | null
    status: 'pending' | 'in_progress' | 'completed'
    score: number | null
    completed_count: number | null
}
```

- **Header**: Status-dependent: `"Practice session ready"` / `"Practice in progress"` / `"Practice completed"`
- **Badge**: `pending`=blue, `in_progress`=amber, `completed`=green
- **Body**: Question count + type breakdown, `focus_topic`, source errors (collapsed)
- **CTA**: `"Open in Classtime"` button -> `session_url`. Disabled if null.
- **Completed**: `score` as percentage, `completed_count / question_count`

### ScheduleWidget

Daily briefing for teachers. Only in `daily_briefing` mode.

```typescript
interface StudentOverview {
    student_id: string
    student_name: string
    next_lesson_time: string
    level: string
    practice_status: 'not_started' | 'in_progress' | 'completed'
    practice_score: number | null
    error_count: number | null
    suggested_focus: string | null
    attention_flag: boolean
}

interface ScheduleData {
    widget_type: 'schedule'
    teacher_id: string
    date: string
    students: StudentOverview[]
}
```

- **Header**: `"{students.length} students today"` with date
- **Per-student card**: Name, time, level badge, practice indicator (`not_started`=red x, `completed`=green check + score)
- **`attention_flag`**: Amber warning icon on card border
- **Expanded**: `suggested_focus`, `error_count`, score breakdown

### DefaultToolResult

Fallback for unregistered widget types. Renders `message` as text,
`data` as collapsible JSON. Ensures new tools work before their widget
is built.

---

## Mode-based UI

Mode is set at session start based on user role. Not switched during conversation.

### daily_briefing (teacher)

| Aspect | Value |
|--------|-------|
| Greeting | `"Good morning, {teacher_name}. You have {n} lessons today."` |
| Default chips | `"Show today's overview"`, `"How is {first_student} doing?"`, `"Who needs attention?"` |
| Tools | `query_daily_overview`, `query_student_report`, `query_errors`, `query_themes`, `query_practice_results` |
| Widgets | ScheduleWidget, ErrorAnalysisWidget, PracticeCardWidget |

After the first response, chips update to show student names from the
overview as quick-access buttons.

### student_practice (student)

| Aspect | Value |
|--------|-------|
| Greeting | `"Hi {student_name}! Let's review your last lesson."` |
| Default chips | `"What errors should I focus on?"`, `"Show my progress"`, `"Open practice session"` |
| Tools | `query_errors`, `query_themes`, `query_level`, `get_practice_session` |
| Widgets | ErrorAnalysisWidget, ThemeMapWidget, PracticeCardWidget |

Students never see `query_daily_overview` or `query_student_report` --
mode-based tool filtering at the backend level.

---

## Chat message types

| Event type | Rendering | Interaction |
|------------|-----------|-------------|
| User message | Right-aligned bubble, plain text | None |
| AI text (`STREAM`) | Left-aligned, markdown via `react-markdown` | Copy button |
| Thinking (`THINKING`) | Collapsed block, muted text, chevron toggle | Expand/collapse |
| Tool step (`TOOL_START`) | Collapsible row: tool name + args + status icon | Expand for full args |
| Tool result (`TOOL_RESULT`) | Widget card routed by `widget_type` | Expand/collapse |
| Status (`STATUS`) | Subtle center-aligned gray text | Auto-dismissed |
| Error | Inline alert with red border + retry suggestion | Retry button |
| Complete (`COMPLETE`) | Invisible. Re-enables input, shows chips. | -- |

### Thinking blocks

`THINKING` events surface the AI's reasoning -- the primary trust mechanism.
Default collapsed with first-line preview. Multiple events accumulate.

PostHog keeps thinking invisible. We diverge intentionally -- Preply's
"Lesson Insights" was perceived as surveillance. Showing reasoning earns
trust by making the AI's decisions transparent.

### Tool step rendering

`TOOL_START` renders as a step indicator with spinner:

```
> query_errors (student: maria_42, severity: moderate+) ... [spinner]
```

On `TOOL_RESULT`, spinner becomes checkmark with duration, widget renders below:

```
v query_errors (student: maria_42, severity: moderate+)  12ms
  [ErrorAnalysisWidget]
```

---

## Loading states

Progressive loading maps to SSE events:

1. **User sends**: Input disables. Status: `"Thinking..."`. Scroll to bottom.
2. **THINKING**: `ThinkingIndicator` with collapsed reasoning preview.
3. **TOOL_START**: Tool step row with name, args summary, spinner. Status: `"Querying errors..."`.
4. **TOOL_RESULT**: Widget replaces spinner placeholder. Fade-in animation.
5. **STREAM**: AI text streams token-by-token below the widget.
6. **COMPLETE**: Input re-enables. Suggested chips appear. Status clears.

---

## ProcessTimeline

Orchestrates thinking, tool calls, and status in a single timeline view.
Borrowed from Medallion's `ProcessTimeline.tsx`.

```typescript
// ProcessTimeline renders three step types
function ProcessTimeline({ steps, isStreaming, toolResults }: Props) {
    return (
        <div className="space-y-2">
            {steps.map((step, idx) => {
                const isActive = isStreaming && idx === steps.length - 1

                switch (step.type) {
                    case 'thinking':
                        return <ThinkingBlock content={step.content} isActive={isActive} />
                    case 'tool_call':
                        const widget = toolResults?.find(r => r.toolId === step.toolId)
                        return <ToolCallBlock step={step} widget={widget} />
                    case 'status':
                        return <StatusStep message={step.message} isActive={isActive} />
                }
            })}
        </div>
    )
}
```

**ThinkingIndicator** accumulates completed steps:
```
✓ Loaded student context (Alex Chen, B1)
✓ Queried lesson errors (9 found)
→ Filtering by severity...
```

Completed steps: green ✓. Current step: spinning loader. On completion,
the entire thinking block collapses to a one-line summary.

**ToolCallBlock** shows tool execution:
```
📋 query_errors                    ✓ 142ms
   └── ErrorAnalysisWidget (expanded below)
```

Running state shows spinner. Completed shows ✓ with execution time.
Failed shows ✗ with error message.

---

## ApprovalDialog

Write operations (creating Classtime sessions) require teacher approval.
Borrowed from Medallion's approval flow.

```typescript
function ApprovalDialog({ request, onApprove, onDeny }: Props) {
    return (
        <Modal title="Review before sending to students">
            <div className="space-y-4">
                <p className="text-sm text-gray-600">{request.description}</p>

                {/* Preview: questions that will be sent */}
                <div className="rounded border p-3">
                    <h4 className="font-medium">Practice session preview</h4>
                    <p>{request.questionCount} questions ({request.types.join(', ')})</p>
                    <p>Focus: {request.focusTopic}</p>
                    {request.sampleQuestions.map(q => (
                        <div key={q.id} className="mt-2 text-sm">{q.content}</div>
                    ))}
                </div>

                <div className="flex justify-end gap-2">
                    <Button variant="secondary" onClick={onDeny}>Edit first</Button>
                    <Button variant="primary" onClick={onApprove}>Send to student</Button>
                </div>
            </div>
        </Modal>
    )
}
```

**Flow**: `create_classtime_session` tool emits APPROVAL event → frontend
shows dialog → teacher reviews questions → approves → session created.

---

### Skeleton states

Between `TOOL_START` and `TOOL_RESULT`, a shimmer placeholder renders
using Tailwind's `animate-pulse`. Matches approximate widget height to
prevent layout shift.

### Error states

- **No skill output**: `ToolFatalError`. AI explains: `"No error analysis found. Analysis may still be running."` No widget.
- **Partial data**: Widget renders available data with a missing-sections note.
- **Network error**: Inline alert with retry button. See reconnection below.

---

## Suggested action chips

Context-aware suggestions appear after each response. Backend includes
`suggestions` in the `COMPLETE` event payload.

| After this result | Chips |
|-------------------|-------|
| `query_daily_overview` | Student names: `"How is Maria doing?"` |
| `query_errors` (grammar heavy) | `"Focus on grammar"`, `"Show vocabulary errors"`, `"Create practice"` |
| `query_student_report` | `"Show errors"`, `"Practice details"`, `"Next student"` |
| `query_practice_results` | `"What errors are still weak?"`, `"Show progress"` |
| `get_practice_session` | `"Open in Classtime"`, `"What should I focus on?"` |
| `query_themes` | `"Show errors for {topic}"`, `"Practice this topic"` |
| `query_level` | `"Show my errors"`, `"What should I practice?"` |

Chips render as a horizontal scrollable row of rounded pill buttons.
Clicking sends the text as the next message. Chips clear on click and
on initial modes come from mode configuration.

---

## Reconnection UX

Chrome extension side panel loses connection on tab switch, network
drop, or sleep. Reconnection must be seamless.

1. **Connection lost**: Status bar shows `"Reconnecting..."` with pulse animation.
2. **Auto-retry**: Exponential backoff, 1s -> 2s -> 4s -> ... -> 30s cap.
3. **Resume**: Browser sends `Last-Event-ID` automatically. Backend resumes from that offset. No duplicates.
4. **Connected**: Brief `"Connected"` status (1.5s), then auto-hides.
5. **Max retries exceeded** (5 attempts): Persistent error with manual `"Reconnect"` button.

SSE reconnection implementation lives in `frontend/src/lib/sse.ts`.
Mirrors PostHog's `XREAD` with `start_id` pattern but without the Redis
layer (see [streaming.md](06-streaming.md)).

---

## Message store

Messages stored as React state array with merge-by-ID:

```typescript
// frontend/src/lib/messageStore.ts
interface ChatMessage {
    id: string
    type: 'user' | 'assistant' | 'thinking' | 'tool_step' | 'widget' | 'status'
    content: string
    timestamp: Date
    toolName?: string
    toolArgs?: Record<string, unknown>
    widgetData?: ToolResultData
    status?: 'pending' | 'complete' | 'error'
}

function mergeMessage(messages: ChatMessage[], incoming: ChatMessage): ChatMessage[] {
    const idx = messages.findIndex((m) => m.id === incoming.id)
    if (idx >= 0) return messages.map((m, i) => (i === idx ? incoming : m))
    return [...messages, incoming]
}
```

Tool start and result share the same `id`. Step starts `pending`
(spinner), updates to `complete` (checkmark) on result.

---

## Conversation history

Teachers and students can see past conversations in a sidebar.

**API endpoints**:
- `GET /api/v1/conversations/` - list recent conversations (title, status, created_at)
- `GET /api/v1/conversations/{id}/` - load full conversation with messages
- `POST /api/v1/conversations/{id}/stream/` - continue an existing conversation

**Sidebar component**:
```typescript
function ConversationSidebar({ conversations }: Props) {
    return (
        <div className="border-r w-64">
            {conversations.map(c => (
                <button key={c.id} onClick={() => loadConversation(c.id)}>
                    <span className="font-medium truncate">{c.title || "New conversation"}</span>
                    <span className="text-xs text-gray-400">{formatRelative(c.created_at)}</span>
                    {c.status === "awaiting_approval" && <Badge>Needs review</Badge>}
                </button>
            ))}
        </div>
    )
}
```

Loading a past conversation fetches all messages and renders them.
Active conversations can be resumed with the stream endpoint.

---

## Component tree and file layout

```
ChatPanel
|-- MessageList
|   |-- UserMessage
|   |-- AssistantMessage (react-markdown)
|   |-- ProcessTimeline
|   |   |-- ThinkingBlock (collapsible, accumulates steps)
|   |   |-- ToolCallBlock (tool name + status + duration)
|   |   +-- StatusStep
|   |-- ThinkingIndicator (collapsible reasoning)
|   |-- ToolStep (collapsible, tool name + status)
|   |-- WidgetMessage -> ToolResultRenderer
|   |   |-- ErrorAnalysisWidget
|   |   |-- ThemeMapWidget
|   |   |-- PracticeCardWidget
|   |   |-- ScheduleWidget
|   |   +-- DefaultToolResult
|   |-- ApprovalDialog (modal for write ops)
|   +-- WidgetSkeleton
|-- SuggestedChips
|-- StatusBar
+-- ChatInput
```

```
frontend/src/
    views/ChatPanel.tsx
    components/
        chat/
            MessageList.tsx, UserMessage.tsx, AssistantMessage.tsx,
            ThinkingIndicator.tsx, ToolStep.tsx, ChatInput.tsx,
            StatusBar.tsx, SuggestedChips.tsx,
            ProcessTimeline.tsx, ApprovalDialog.tsx
        widgets/
            ToolResultRenderer.tsx, ErrorAnalysisWidget.tsx,
            ThemeMapWidget.tsx, PracticeCardWidget.tsx,
            ScheduleWidget.tsx, DefaultToolResult.tsx, WidgetSkeleton.tsx
    lib/
        sse.ts, messageStore.ts, constants.ts
    api/hooks/useChat.ts
```

---

## Key differences from Medallion

| Pattern | Medallion | Preply | Why |
|---------|-----------|--------|-----|
| Conversation sidebar | Full sidebar with history + token counts | No sidebar -- single-session side panel | Extension width constraint |
| Mode indicator | Inline divider on mode switch | Mode fixed at session start | Two roles, not a multi-mode agent |
| Memory panel | User-facing memory management | No memory in MVP | Query-only, no preference storage |
| Cost display | Token counts in sidebar | Not shown | Hackathon scope |
| Approval modal | Modal for dangerous ops | ApprovalDialog for write ops (Classtime sessions) | Teachers review before sending to students |

---

## Implementation sequence

1. **ChatPanel + MessageList + ChatInput**: Chat shell, SSE via `useChat`.
2. **ThinkingIndicator + ToolStep + StatusBar**: Trust layer rendering.
3. **ErrorAnalysisWidget**: Primary widget with grouped errors + severity badges.
4. **SuggestedChips**: Context-aware from `COMPLETE` payload.
5. **PracticeCardWidget + ThemeMapWidget**: Session status + theme clusters.
6. **ScheduleWidget**: Teacher daily overview.
7. **Reconnection**: Exponential backoff + `Last-Event-ID` resume.
8. **WidgetSkeleton + loading polish**: Shimmer, progressive loading, error states.
