# State persistence

> Inspired by [PostHog's Max AI assistant](https://github.com/PostHog/posthog).
> Source: [`ee/models/assistant.py`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py)

## At a glance

**What this covers**: How skill execution state and conversation state are tracked - the SkillExecution state machine, Conversation/ChatMessage persistence, the two-repo execution model, and Temporal workflows for both skills and the chat agent.

**Why it matters**: Skills are expensive multi-step LLM calls. Tracking state prevents lost work, enables retry, and lets query tools find completed results.

**Key terms**:

| Term | Meaning |
|------|---------|
| SkillExecution | Django model tracking one skill run: status, input_data, output_data |
| Status | PENDING → RUNNING → COMPLETED / FAILED |
| output_data | JSONField where completed skills store structured results. Query tools read from here |
| Two-repo model | Skills live in preply-lesson-ai-skills (Claude Code commands), app lives here. `output_data` is the contract |
| Worker | Temporal worker process that executes skill and chat agent activities |
| Temporal | Durable workflow engine for both skill pipelines and the chat agent |
| Conversation | Django model tracking a chat session: teacher/student, mode, status, linked lesson |
| ChatMessage | Persisted message record: role, content, tool_calls. Every message saved to DB as it happens |

**Prerequisites**: [skill-system.md](../skill-system.md)

---

LLM calls are expensive to retry. A crashed workflow that loses state means
re-running API calls that already cost money. This doc examines how PostHog
solves state persistence and what we adapt for our simpler skill-based
architecture.

---

## What PostHog does

PostHog's Max AI assistant persists conversation state across three layers:
Django models for metadata, LangGraph checkpoints for graph execution state,
and Temporal workflows for crash-resilient orchestration.

### Conversation model

The `Conversation` model tracks high-level session state:

```python
# ee/models/assistant.py
class Conversation(UUIDTModel):
    class Status(models.TextChoices):
        IDLE = "idle", "Idle"
        IN_PROGRESS = "in_progress", "In progress"
        CANCELING = "canceling", "Canceling"

    class Type(models.TextChoices):
        ASSISTANT = "assistant", "Assistant"
        TOOL_CALL = "tool_call", "Tool call"
        DEEP_RESEARCH = "deep_research", "Deep research"
        SLACK = "slack", "Slack"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IDLE)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.ASSISTANT)
    title = models.CharField(null=True, blank=True, max_length=250)
```

Key design choices:

- **Status enum** (`IDLE`/`IN_PROGRESS`/`CANCELING`) enables reconnection.
  When a user returns to a conversation with `status != IDLE`, the executor
  knows a workflow is active and skips creating a new one.
- **Type enum** separates conversation modes. Each type has different
  execution paths -- `ASSISTANT` uses LangGraph, `SLACK` routes through
  Slack integration, `DEEP_RESEARCH` runs long-form analysis.
- **`approval_decisions`** JSONField stores metadata for dangerous operation
  approvals. Format: `{proposal_id: {decision_status, tool_name, preview}}`.
  The actual payload lives in the checkpoint; this field tracks decisions.
- **`messages_json`** stores messages for non-LangGraph modes (sandbox).
  LangGraph modes persist messages through the checkpoint system instead.

### LangGraph checkpoint storage

Three Django models implement LangGraph's
[`BaseCheckpointSaver`](https://github.com/PostHog/posthog/blob/master/ee/hogai/django_checkpoint/checkpointer.py)
protocol:

| Model | Key fields | Purpose |
|-------|-----------|---------|
| [`ConversationCheckpoint`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py#L100) | `thread` FK, `checkpoint_ns`, `parent_checkpoint` self-FK, `checkpoint` JSON, `metadata` JSON | Main checkpoint with parent chain for traversal |
| [`ConversationCheckpointBlob`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py#L125) | `channel`, `version`, `blob` binary | Channel values (messages, state fields) per version |
| [`ConversationCheckpointWrite`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py#L151) | `task_id`, `idx`, `channel`, `blob` binary | Intermediate writes enabling resume-from-interrupt |

`checkpoint_ns` isolates subgraph state (e.g. `"child|grandchild"`).
The checkpointer partitions by `thread_id` (conversation UUID).

### Temporal workflows for durability

Each conversation maps to a Temporal workflow:

```python
# ee/hogai/core/executor.py
handle = await client.start_workflow(
    workflow.run,
    inputs,
    id=self._workflow_id,                                       # "conversation-{uuid}"
    task_queue=settings.MAX_AI_TASK_QUEUE,
    id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,   # reconnect to running
    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,      # restart completed
)
```

Temporal checkpoints state after each activity completes. If a crash happens
at step 3, the workflow resumes from step 3. The `id_conflict_policy` of
`USE_EXISTING` means reconnecting to a conversation joins the running
workflow rather than creating a new one.

### Crash recovery flow

1. User reconnects to conversation with `status != IDLE`
2. `AgentExecutor` detects active workflow, skips new workflow creation
3. Reads Redis stream for any buffered messages
4. If Temporal workflow still running, continues streaming from it

### CoreMemory

Separate from conversation state, PostHog persists long-term team knowledge
in a [`CoreMemory`](https://github.com/PostHog/posthog/blob/master/ee/models/assistant.py#L176)
model: one row per team, `text` field (newline-separated facts), capped at
5000 characters with head+tail truncation. The AI self-manages memory via
async `aappend_core_memory` and `areplace_core_memory` methods.

---

## What we take

Our architecture has different persistence needs. PostHog runs interactive
conversations with multi-step graph execution. We run background skills that
produce structured output, then serve that output through a chat layer.

### SkillExecution: the core state machine

Every AI workflow is a `SkillExecution` with a simple four-state lifecycle:

```python
class SkillExecutionStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SkillExecution(TimeStampedModel):
    teacher = ForeignKey(Teacher, on_delete=CASCADE, related_name="skill_executions")
    lesson = ForeignKey(Lesson, on_delete=CASCADE, null=True, blank=True,
                        related_name="skill_executions")
    student = ForeignKey(Student, on_delete=CASCADE, null=True, blank=True,
                         related_name="skill_executions")
    skill_name = CharField(max_length=100, db_index=True)
    status = CharField(max_length=20, choices=SkillExecutionStatus.choices, db_index=True)
    started_at = DateTimeField(null=True, blank=True)
    completed_at = DateTimeField(null=True, blank=True)
    input_data = JSONField(default=dict)   # skill inputs (transcript, config)
    output_data = JSONField(default=dict)  # structured skill output
    output_log = TextField(blank=True)     # stdout capture
    error = TextField(blank=True)          # stderr on failure
    exit_code = IntegerField(null=True, blank=True)
```

State transitions:

```
PENDING -----> RUNNING -----> COMPLETED
                  |
                  +---------> FAILED
```

Compared to PostHog's `Conversation.Status` (`IDLE`/`IN_PROGRESS`/`CANCELING`),
we have four states instead of three. The difference: PostHog tracks whether
a conversation *can accept new input*, while we track whether a background
job *has finished producing output*. PostHog needs `CANCELING` because users
can interrupt mid-stream. Our skills run unattended -- they either complete
or fail.

The `CheckConstraint` enforces that every execution is scoped to at least
one entity:

```python
    constraints = [
        CheckConstraint(
            check=Q(lesson__isnull=False) | Q(student__isnull=False),
            name="skill_exec_requires_lesson_or_student",
        ),
    ]
```

This matters because different skills scope differently:
- `analyze-lesson-errors` is lesson-scoped (lesson + student set)
- `prepare-daily-briefing` is student-scoped (student set, no lesson)

### Temporal workflows

Both the skill pipeline and the chat agent run as Temporal workflows.
Temporal gives us crash recovery, automatic retry, and workflow visibility
for both paths.

```python
# Two Temporal workflows

@workflow.defn(name="lesson-analysis")
class LessonAnalysisWorkflow:
    """Background skill pipeline - runs after each lesson."""
    @workflow.run
    async def run(self, input: LessonAnalysisInput) -> None:
        # 1. fetch_transcript
        # 2-4. analyze_errors, analyze_themes, analyze_level (parallel)
        # 5. generate_questions (waits for 2-4)
        # 6. create_classtime_session

@workflow.defn(name="chat-agent")
class ChatAgentWorkflow:
    """Conversational agent - runs per user message."""
    @workflow.run
    async def run(self, input: ChatAgentInput) -> None:
        await workflow.execute_activity(
            run_chat_agent,
            input,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

@activity.defn
async def run_chat_agent(input: ChatAgentInput) -> None:
    writer = StreamWriter(input.conversation_id)
    conversation = await Conversation.objects.aget(id=input.conversation_id)
    agent = PreplyAgent(mode=input.mode, context=input.context)

    async for event in agent.run(input.message, conversation=conversation):
        await writer.write(event)
        activity.heartbeat()
```

`LessonAnalysisWorkflow` orchestrates the multi-step skill pipeline with
parallel fan-out and dependency ordering. `ChatAgentWorkflow` wraps
the agent loop as a single activity with heartbeats so Temporal can
detect stuck workers and retry.

## Two-repo execution model

Skills and the app live in separate repos with `SkillExecution.output_data`
as the contract between them.

```
preply-lesson-ai-skills/              preply-lesson-intelligence/
─────────────────────────             ──────────────────────────
.claude/skills/                       backend/apps/skill_results/
  analyze-lesson-errors/                SkillExecution model
  analyze-lesson-themes/                  ├── output_data (JSONField)
  generate-classtime-questions/           ├── status
  ...                                     └── input_data

src/lesson_ai/                        backend/services/ai_chat/tools/
  CLI: preply-lesson-ai                   query tools READ from output_data
  pushes skill output to backend          never execute skills
                                          pure readers + formatters
```

**Contract**: `output_data` format is the boundary. Skills produce it, query
tools consume it. Neither side cares how the other is implemented.

### Skill execution: from CLI to Temporal

The skill pipeline has a clear progression path. The contract (`output_data`)
never changes - only the execution engine evolves.

**Phase 0: Manual (hackathon start)**

Run a skill by hand. No worker, no automation. The fastest way to iterate
on skill quality - tweak the prompt, re-run, compare output.

```bash
# 1. Fetch transcript from backend
preply-lesson-ai transcripts fetch <lesson_id>

# 2. Run the skill (Claude Code slash command)
preply-lesson-ai /analyze-lesson-errors <lesson_id>

# 3. Push output to backend
preply-lesson-ai skill-results push <lesson_id>
```

The skill fetches its own input, reads theory references, analyzes, writes
structured JSON to `storage/skill-results/`, and the CLI pushes it to the
backend. The backend stores it in `SkillExecution.output_data`. Query tools
can read it immediately. The chat agent doesn't know or care how the data
got there.

**Phase 1: Worker automation (hackathon demo)**

A simple polling worker automates what you did manually in Phase 0.
Still no Temporal for skills - just a loop.

```python
# worker/skill_worker.py
while True:
    pending = requests.get(f"{API_URL}/skill-executions/pending/").json()
    for execution in pending:
        requests.patch(f"{API_URL}/skill-executions/{execution['id']}/",
                       json={"status": "running"})
        result = subprocess.run(
            ["claude", "-p", f"/{execution['skill_name']}", ...],
            capture_output=True, text=True,
        )
        # PATCH completed/failed with output_data
    time.sleep(5)
```

Good enough for the demo: lesson created → worker picks up skills → results
appear in chat. The chat agent (which uses Temporal + Redis) consumes the
same `output_data` regardless of how it was produced.

**Phase 2: Temporal orchestration (post-hackathon)**

Same `SkillExecution` model, same `output_data` format. The worker becomes
a Temporal worker. Skills become activities with retry policies and
checkpointing. The query tools don't change at all.

```python
# workflows/lesson_analysis.py (post-hackathon)
@workflow.defn(name="lesson-analysis")
class LessonAnalysisWorkflow:
    @workflow.run
    async def run(self, input: LessonAnalysisInput) -> None:
        transcript = await workflow.execute_activity(fetch_transcript, input.lesson_id)

        # Parallel analysis - all three run concurrently
        errors, themes, level = await asyncio.gather(
            workflow.execute_activity(analyze_errors, transcript,
                                      retry_policy=RetryPolicy(maximum_attempts=2)),
            workflow.execute_activity(analyze_themes, transcript,
                                      retry_policy=RetryPolicy(maximum_attempts=2)),
            workflow.execute_activity(analyze_level, transcript,
                                      retry_policy=RetryPolicy(maximum_attempts=2)),
        )

        # Sequential - depends on analysis results
        questions = await workflow.execute_activity(generate_questions, errors, themes, level)
        await workflow.execute_activity(create_classtime_session, questions)
```

**What changes**: execution engine (polling → Temporal).
**What stays**: `SkillExecution` model, `output_data` format, query tools,
the API endpoints, the CLI commands. Everything downstream is identical.

### DailyBriefing as pre-computed cache

```python
class DailyBriefing(TimeStampedModel):
    teacher = ForeignKey(Teacher, on_delete=CASCADE, related_name="daily_briefings")
    date = DateField(db_index=True)
    briefing_data = JSONField(default=dict)
    generated_at = DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("teacher", "date")]
```

One row per teacher per date. The overnight pipeline aggregates all skill
outputs and practice results for tomorrow's students, runs
`prepare-daily-briefing`, and stores the result. The teacher's morning
chat reads directly from this cache:

```python
DailyBriefing.objects.get(teacher=teacher, date=today)
```

No on-demand computation. The briefing is ready before the teacher opens
the app. This is analogous to PostHog's `CoreMemory` -- pre-computed
knowledge that the AI reads rather than generates in real time.

### TutoringRelationship denormalized aggregates

```python
class TutoringRelationship(TimeStampedModel):
    teacher = ForeignKey(Teacher, on_delete=CASCADE)
    student = ForeignKey(Student, on_delete=CASCADE)
    # ...subject, level, goal, schedule fields...
    total_lessons = IntegerField(default=0)
    last_lesson_at = DateTimeField(null=True, blank=True)
    status = CharField(max_length=20, choices=TutoringStatus.choices,
                       default=TutoringStatus.ACTIVE, db_index=True)

    class Meta:
        unique_together = [("teacher", "student", "subject_type")]
```

`total_lessons` and `last_lesson_at` are denormalized -- updated after each
lesson completes rather than computed via `COUNT(*)` queries. This keeps
reads fast for the daily briefing and chat context injection, which pull
these aggregates frequently.

## Conversation persistence

Every chat session is a `Conversation` with persisted `ChatMessage` records.
No in-memory shortcuts - messages are saved to DB as they happen.

Adapted from Medallion's production model
([`apps/ai_chat/models.py`](https://github.com/PostHog/posthog)).

### Models

```python
class Conversation(TimeStampedModel):
    teacher = ForeignKey(Teacher, null=True, blank=True)
    student = ForeignKey(Student, null=True, blank=True)
    mode = CharField(max_length=30)  # daily_briefing, student_practice
    lesson = ForeignKey(Lesson, null=True, blank=True)
    status = CharField(choices=ConversationStatus.choices)  # active, awaiting_approval, completed, failed
    status_metadata = JSONField(default=dict)  # approval_id, pending_tool_use
    title = CharField(max_length=255, blank=True)

class ChatMessage(TimeStampedModel):
    conversation = ForeignKey(Conversation)
    role = CharField(choices=MessageRole.choices)  # user, assistant, tool_result
    content = TextField()
    tool_calls = JSONField(null=True)    # [{id, name, input}]
    tool_use_id = CharField(null=True)   # for tool_result messages
    tool_name = CharField(null=True)     # for tool_result messages
    stop_reason = CharField(null=True)   # tool_use, end_turn
    metadata = JSONField(null=True)      # thinking_steps, process_steps

class ToolExecution(TimeStampedModel):
    conversation = ForeignKey(Conversation)
    message = ForeignKey(ChatMessage, null=True)
    tool_name = CharField(max_length=100)
    tool_use_id = CharField(max_length=100)
    input_args = JSONField()
    success = BooleanField(default=True)
    result_message = TextField()
    result_data = JSONField(null=True)
    execution_time_ms = IntegerField(default=0)
    requires_approval = BooleanField(default=False)

class ApprovalRequest(TimeStampedModel):
    conversation = ForeignKey(Conversation)
    tool_execution = OneToOneField(ToolExecution, null=True)
    tool_name = CharField(max_length=100)
    tool_input = JSONField()
    description = TextField()
    status = CharField(choices=ApprovalStatus.choices)  # pending, approved, rejected
```

### How messages persist during the agent loop

```python
# 1. User sends message → save to DB
user_msg = await ChatMessage.objects.acreate(
    conversation=conversation, role="user", content=user_input,
)

# 2. LLM responds with tool_use → save assistant message with tool_calls
assistant_msg = await ChatMessage.objects.acreate(
    conversation=conversation, role="assistant",
    content=text_content, tool_calls=tool_calls_json,
    stop_reason="tool_use",
)

# 3. Tool executes → save tool_result message + ToolExecution record
tool_msg = await ChatMessage.objects.acreate(
    conversation=conversation, role="tool_result",
    content=result_message, tool_use_id=tool_id, tool_name=tool_name,
)
await ToolExecution.objects.acreate(
    conversation=conversation, message=assistant_msg,
    tool_name=tool_name, tool_use_id=tool_id,
    input_args=input_args, success=True,
    result_message=result_message, result_data=result_data,
    execution_time_ms=elapsed_ms,
)

# 4. Final response → save assistant message
final_msg = await ChatMessage.objects.acreate(
    conversation=conversation, role="assistant",
    content=final_text, stop_reason="end_turn",
    metadata={"thinking_steps": steps, "process_steps": process},
)
```

### Conversation state machine

```
ACTIVE → AWAITING_APPROVAL → ACTIVE → COMPLETED
           (teacher reviews)
ACTIVE → COMPLETED (user closes)
ACTIVE → FAILED (error)
```

`status_metadata` stores rich state without schema changes:
- Approval: `{"approval_id": "...", "pending_tool_use": {...}}`
- Checkpoint: `{"last_iteration": 3}`

### Why persist everything

- **History**: teacher sees past conversations in sidebar
- **Reconnection**: extension reopens → load conversation from DB
- **Debugging**: every tool call logged with input/output/timing
- **Trust**: user can review what the AI did in past sessions
- **Analytics**: which tools are used most, where errors happen

---

## What we skip (and why)

### LangGraph checkpointing

PostHog's three-table checkpoint system (`ConversationCheckpoint`,
`ConversationCheckpointBlob`, `ConversationCheckpointWrite`) supports
complex multi-step graph execution with interrupt/resume, subgraph
isolation, and channel-level versioning.

We skip this because our skills are single-shot: one LLM call that reads
input and produces output. There is no graph to checkpoint. The
`SkillExecution` status field gives us the only state tracking we need.

### Cost tracking per message

PostHog tracks token usage and cost per LLM call. We skip per-message
cost tracking for now -- aggregate cost monitoring at the API key level
is sufficient for hackathon. Add per-conversation cost tracking when
we need to understand cost-per-teacher or cost-per-feature.

### Cross-session memory

PostHog's `CoreMemory` lets the AI self-manage persistent facts across
conversations. We skip this -- `TutoringRelationship` aggregates and
`DailyBriefing` cache provide the cross-session context we need without
giving the AI write access to its own memory store.

---

## Implementation notes

### SkillExecution lifecycle in practice

```
1. Lesson transcript arrives
2. LessonAnalysisWorkflow starts, creates SkillExecutions:
   - analyze-lesson-errors    (PENDING, lesson=L, student=S)
   - analyze-lesson-themes    (PENDING, lesson=L, student=S)
   - analyze-lesson-level     (PENDING, lesson=L, student=S)
3. Temporal runs all three as parallel activities -> RUNNING
4. Skills complete -> COMPLETED with output_data
5. Workflow detects all three COMPLETED
6. Creates: generate-classtime-questions (PENDING, lesson=L, student=S)
   - input_data includes output references from steps 2-4
7. Temporal runs question generation activity -> COMPLETED
8. Workflow creates Classtime session, notifies student
```

Each step is a separate `SkillExecution` record. `LessonAnalysisWorkflow`
orchestrates the dependency graph - Temporal handles retry and crash
recovery automatically.

### Stale execution detection

Temporal handles activity retry automatically - if a worker crashes,
the activity is rescheduled per its `RetryPolicy`. As a safety net,
a reaper query catches any `SkillExecution` records stuck in `RUNNING`
(e.g., if the Temporal workflow itself was terminated):

```python
stale = SkillExecution.objects.filter(
    status=SkillExecutionStatus.RUNNING,
    started_at__lt=timezone.now() - timedelta(minutes=10),
)
stale.update(status=SkillExecutionStatus.PENDING, started_at=None)
```

### DailyBriefing generation

The overnight job queries `TutoringRelationship` for teachers with lessons
tomorrow, then queues `prepare-daily-briefing` skill executions.

Design tension: the `CheckConstraint` requires `lesson` or `student`, but
daily briefings are teacher-scoped. Resolution: create one `SkillExecution`
per student (each with focused input/output), then aggregate results into
a single `DailyBriefing` row. The constraint stays honest.

---

## Comparison table

| Concern | PostHog | Lesson Intelligence |
|---------|---------|---------------------|
| Conversation state | `Conversation.status` (IDLE/IN_PROGRESS/CANCELING) | `SkillExecution.status` (PENDING/RUNNING/COMPLETED/FAILED) |
| Conversation types | 4 types with different execution paths | 2 modes (`daily_briefing`, `student_practice`) on `Conversation.mode` |
| Message persistence | LangGraph checkpoints + `messages_json` fallback | `Conversation` + `ChatMessage` models, persisted to DB |
| Graph state | 3-table checkpoint system (checkpoint, blob, write) | Not needed -- no graph execution |
| Workflow orchestration | Temporal with crash recovery | Temporal for both skills + chat agent |
| Long-term memory | `CoreMemory` (team-scoped, self-managed) | `TutoringRelationship` aggregates + `DailyBriefing` cache |
| Dangerous operations | `approval_decisions` JSONField | `ApprovalRequest` model with `ToolExecution` link |
| Crash recovery | Resume from exact Temporal/LangGraph step | Temporal retry per activity (skills re-run, chat agent resumes via heartbeat) |
