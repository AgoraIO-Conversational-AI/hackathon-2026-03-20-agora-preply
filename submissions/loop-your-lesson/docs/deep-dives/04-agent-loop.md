# Agent loop

> Inspired by [PostHog's Max AI assistant](https://github.com/PostHog/posthog).
> Source: [`ee/hogai/core/`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/)

## At a glance

**What this covers**: The while-loop that powers AI conversations - no LLM frameworks (no LangGraph), direct LLM API (provider-agnostic), tool dispatch, Temporal for execution durability, and the extensible mode system.

**Why it matters**: This is the core of the chat experience. Every question a teacher or student asks flows through the agent loop.

**Key terms**:

| Term | Meaning |
|------|---------|
| Agent loop | A `while` loop: call LLM → tool_use? → execute tools → loop back → until done |
| tool_use / stop_reason | LLM's signal that it wants to call a tool vs respond directly (Anthropic: `stop_reason`, OpenAI: `finish_reason`) |
| Mode | `daily_briefing` (teacher) or `student_practice` (student). Determines available tools and system prompt |
| MODE_TOOLS | Dict mapping each mode to its available tool names |
| Query tools | Read-only tools that fetch pre-computed skill output. The agent never triggers skill execution |

**Prerequisites**: [tool-system.md](03-tool-system.md), [conversational-ux.md](../conversational-ux.md)

---

## What PostHog does

PostHog's Max AI uses a ROOT / ROOT_TOOLS loop built on LangGraph. The
core is two files: `AgentLoopGraph` defines the graph structure,
`BaseAgentRunner` streams its execution.

### The graph: ROOT / ROOT_TOOLS

[`loop_graph/graph.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/loop_graph/graph.py)
defines the minimal cycle:

```python
class AgentLoopGraph(BaseAssistantGraph[AssistantState, PartialAssistantState]):
    def add_agent_node(self, router=None, is_start_node=False):
        root_node = AgentLoopGraphNode(
            self._team, self._user, self.mode_manager_class, AgentLoopNodeType.ROOT
        )
        self.add_node(AssistantNodeName.ROOT, root_node)
        if is_start_node:
            self._graph.add_edge(AssistantNodeName.START, AssistantNodeName.ROOT)
        self._graph.add_conditional_edges(AssistantNodeName.ROOT, root_node.router)
        return self

    def add_agent_tools_node(self, router=None):
        agent_tools_node = AgentLoopGraphNode(
            self._team, self._user, self.mode_manager_class, AgentLoopNodeType.TOOLS
        )
        self.add_node(AssistantNodeName.ROOT_TOOLS, agent_tools_node)
        self._graph.add_conditional_edges(
            AssistantNodeName.ROOT_TOOLS, agent_tools_node.router,
            path_map={"root": AssistantNodeName.ROOT, "end": AssistantNodeName.END},
        )
        return self

    def compile_full_graph(self, checkpointer=None):
        return self.add_agent_node(is_start_node=True).add_agent_tools_node().compile(...)
```

The `path_map` constrains ROOT_TOOLS to exactly two destinations: back
to `root` or `end`.

```
START --> ROOT --> (tool_use?) --> ROOT_TOOLS --> (done?) --> ROOT --> ... --> END
```

### Node delegation through mode managers

Each node delegates to a mode manager that picks behavior based on
`state.agent_mode`. From
[`loop_graph/nodes.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/loop_graph/nodes.py):

```python
class AgentLoopGraphNode(AssistantNode):
    async def arun(self, state: AssistantState, config: RunnableConfig):
        manager = self._mode_manager_class(
            team=self._team, user=self._user,
            node_path=self.node_path,
            context_manager=self.context_manager,
            state=state,
        )
        node = manager.node if self._node_type == AgentLoopNodeType.ROOT else manager.tools_node
        return await node(state, config)

    def router(self, state: AssistantState):
        # BUG: LangGraph calls this router when resuming an interruption,
        # but there is no available config
        self._config = RunnableConfig(configurable={})
        manager = self._mode_manager_class(...)
        node = manager.node if self._node_type == AgentLoopNodeType.ROOT else manager.tools_node
        return node.router(state)
```

The `# BUG` comment is telling. LangGraph's interrupt-resume flow forces
the router to be called without config, requiring a workaround.

### Streaming execution

[`runner.py`](https://github.com/PostHog/posthog/blob/master/ee/hogai/core/runner.py)
defines `BaseAgentRunner.astream()`, which wraps LangGraph's stream in
400+ lines of error handling:

```python
async def astream(self, ...) -> AsyncGenerator[AssistantOutput, None]:
    state = await self._init_or_update_state()
    config = self._get_config()
    generator = self._graph.astream(state, config=config, ...)

    async with self._lock_conversation():
        try:
            async for update in generator:
                if messages := await self._process_update(update):
                    for message in messages:
                        yield AssistantEventType.MESSAGE, message
        except GraphRecursionError:
            yield AssistantEventType.MESSAGE, AssistantMessage(
                content="I've reached the maximum number of steps..."
            )
        except LLM_CLIENT_EXCEPTIONS as e:
            # Client/validation errors (400, 422) - won't resolve on retry
            yield AssistantEventType.MESSAGE, FailureMessage(...)
        except LLM_TRANSIENT_EXCEPTIONS as e:
            # Transient errors (5xx, rate limits) - may resolve on retry
            yield AssistantEventType.MESSAGE, FailureMessage(...)
        except Exception as e:
            # Unhandled - reset state, stop generation
            ...
```

Each exception category resets the graph state and yields a failure
message. The `recursion_limit` is set to 96 in `_get_config()`.

### Why single loop beats subagents

PostHog learned this the hard way. From their codebase
([`chat_agent/graph.py:46`](https://github.com/PostHog/posthog/blob/master/ee/hogai/chat_agent/graph.py)):

```python
# Subgraphs incorrectly merge messages, so please don't use them here.
```

Subagents lose context at every transition. The mode manager pattern
keeps everything in one graph with one message list. Different modes
(Analytics, SQL, Replay) share the same loop -- the mode manager swaps
behavior, not structure.

### PostHog's own recommendation

PostHog uses LangGraph but recommends against it. From their
documentation: "PostHog currently uses LangChain/LangGraph but is moving
away from it and would not recommend it."

Their codebase shows why. The `AgentLoopGraph` wraps LangGraph in a
two-node graph that is functionally a while loop. The `BaseAgentRunner`
adds 400+ lines to handle LangGraph's streaming, checkpointing, and
interrupt semantics. The `# BUG` comment in the router shows framework
friction in practice.

The abstraction cost is real: `BaseAssistantGraph` + `AgentLoopGraph` +
`AgentLoopGraphNode` + `AgentModeManager` + `BaseAgentRunner` -- five
classes to express "call LLM, execute tools, repeat."

---

## What we take

We take the pattern, not the framework. A simple while loop with direct
LLM SDK calls. Provider-agnostic - works with Anthropic or OpenAI. The
loop runs inside a Temporal activity and writes events to a Redis
StreamWriter instead of yielding directly.

### Agent loop

```python
# backend/services/ai_chat/agent.py

from temporalio import activity

from backend.services.ai_chat.llm import get_llm_client, LLMResponse
from backend.services.ai_chat.tools.base import PreplyTool
from backend.services.ai_chat.modes import Mode, get_mode
from backend.services.ai_chat.context import build_system_prompt
from backend.services.ai_chat.stream_events import StreamEvent, StreamEventType
from backend.services.ai_chat.stream import StreamWriter

MAX_ITERATIONS = 10


async def run_agent_loop(
    *,
    writer: StreamWriter,
    messages: list[dict],
    mode: Mode,
    context: dict,
) -> None:
    """
    The agent loop. Call LLM, execute tools, loop back.
    No LLM framework, no graph, no state machine - but runs inside a
    Temporal activity for execution durability.
    Provider-agnostic: works with Anthropic (Claude) or OpenAI (GPT).
    """
    client = get_llm_client()  # Returns Anthropic or OpenAI client based on settings
    tools = mode.get_tools()
    tool_registry: dict[str, PreplyTool] = {t.name: t for t in tools}
    system_prompt = build_system_prompt(mode=mode, context=context)

    tool_schemas = [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.args_schema.model_json_schema(),
        }
        for t in tools
    ]

    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1

        # Call LLM (provider-agnostic)
        response: LLMResponse = await client.chat(
            system=system_prompt,
            messages=messages,
            tools=tool_schemas,
        )

        # Extract text and tool_use blocks
        assistant_message = {"role": "assistant", "content": response.content}
        messages.append(assistant_message)

        # Write any text content to the stream
        for block in response.content:
            if block.type == "text":
                await writer.write(StreamEvent(type=StreamEventType.STREAM, data=block.text))
                activity.heartbeat()

        # No tool calls -- done
        if response.stop_reason != "tool_use":
            await writer.write(StreamEvent(type=StreamEventType.COMPLETE, data=None))
            activity.heartbeat()
            return

        # Execute each tool call
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool = tool_registry.get(block.name)
            if not tool:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Unknown tool: {block.name}",
                    "is_error": True,
                })
                continue

            await writer.write(StreamEvent(
                type=StreamEventType.TOOL_START,
                data={"tool": block.name, "input": block.input},
            ))
            activity.heartbeat()

            try:
                validated = tool.validate_args(**block.input)
                message, data = await tool.execute(**validated.model_dump())

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": message,
                })

                await writer.write(StreamEvent(
                    type=StreamEventType.TOOL_RESULT,
                    data={"tool": block.name, "message": message, "widget_data": data},
                ))
                activity.heartbeat()
            except Exception as e:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Tool error: {str(e)}",
                    "is_error": True,
                })

        # Append tool results and loop back
        messages.append({"role": "user", "content": tool_results})

    # Safety: hit max iterations
    await writer.write(StreamEvent(
        type=StreamEventType.STREAM,
        data="I've reached the maximum number of steps. Could you rephrase your question?",
    ))
    activity.heartbeat()
    await writer.write(StreamEvent(type=StreamEventType.COMPLETE, data=None))
    activity.heartbeat()
```

### Supporting pieces

**Mode configuration** (`modes.py`): A `Mode` dataclass holds `name`,
`instructions`, and `tool_classes`. `MODES` dict maps `"daily_briefing"`
and `"student_practice"` to their configs. Same loop, different tools
and prompt. Replaces PostHog's `AgentModeManager` class hierarchy.

**Tool registry**: `{t.name: t for t in tools}` -- a flat dict built at
the start of each turn. PostHog routes through node paths, context
managers, and config propagation. Our dict does the same job.

**System prompt** (`context.py`): `build_system_prompt()` concatenates
mode instructions + context layers (lesson, student, pedagogical) +
tool-specific context prompts. Stable prefix enables prompt caching.
PostHog injects context at the same position for the same reason.

### What maps to what

| PostHog component | Lines of code | Our equivalent | Lines of code |
|---|---|---|---|
| `BaseAssistantGraph` | 98 | (not needed) | 0 |
| `AgentLoopGraph` | 54 | (not needed) | 0 |
| `AgentLoopGraphNode` | 56 | (not needed) | 0 |
| `AgentModeManager` | ~200 | `Mode` dataclass | ~30 |
| `BaseAgentRunner.astream()` | ~460 | `run_agent_loop()` | ~90 |
| LangGraph dependency | -- | LLM SDK (Anthropic or OpenAI) | -- |
| Django checkpointer | ~300 | Conversation + ChatMessage models | ~50 |

Total: ~1170 lines of framework plumbing replaced by ~170 lines of
direct SDK code + Django models.

## Extensible mode system

Two modes for hackathon, designed for growth. Borrowed from Medallion's
`AgentMode` + `AgentToolkit` pattern.

```python
class AgentMode(StrEnum):
    DAILY_BRIEFING = "daily_briefing"
    STUDENT_PRACTICE = "student_practice"
    # Future: LESSON_DEEP_DIVE, CROSS_SESSION_REVIEW, PARENT_REPORT

MODE_TOOLS: dict[AgentMode, list[str]] = {
    AgentMode.DAILY_BRIEFING: [
        "query_daily_overview", "query_student_report",
        "query_errors", "query_themes", "query_practice_results",
        "query_schedule",
    ],
    AgentMode.STUDENT_PRACTICE: [
        "query_errors", "query_themes", "query_level",
        "get_practice_session", "query_practice_results",
        "get_transcript_segment",
    ],
}

MODE_PROMPTS: dict[AgentMode, str] = {
    AgentMode.DAILY_BRIEFING: (
        "You are helping teacher {teacher_name} prepare for today's lessons. "
        "Analysis has already been completed for each student. "
        "Use query tools to explore pre-computed results."
    ),
    AgentMode.STUDENT_PRACTICE: (
        "You are helping {student_name} review their last lesson. "
        "Lesson analysis is already available. Use query tools to show "
        "errors, themes, level assessment, and practice results. "
        "Students can also see their transcript segments."
    ),
}

MODE_CHIPS: dict[AgentMode, list[str]] = {
    AgentMode.DAILY_BRIEFING: [
        "Show today's overview",
        "How is {student_name} doing?",
        "What should I focus on with {student_name}?",
    ],
    AgentMode.STUDENT_PRACTICE: [
        "What errors should I focus on?",
        "How did I do on practice?",
        "Show me when I said that",
        "What's my level?",
    ],
}
```

**Adding a mode** = add enum value + tool list + prompt + chips. Agent loop
doesn't change. Mode is set from `ExtensionContext.page_type` at conversation
start, not switchable mid-conversation.

**Student mode is rich** - students can:
- See errors with corrections, explanations, and reasoning
- Ask "Why is this wrong?" → AI references error taxonomy reasoning
- Review Classtime practice results ("How did I do?")
- See which errors they mastered vs still making
- Pull transcript segments ("Show me when I said that")
- Check CEFR level with strengths and gaps

### Tools read pre-computed skill output

All tools in the agent loop are **query tools** - they read from
`SkillExecution.output_data`, never trigger skill execution. The system prompt
explicitly tells the AI:

> "Lesson analysis has already been completed in the background. Use the
> available query tools to explore and present results to the user."

This means the agent loop is fast (DB reads only, no LLM calls inside tools)
and deterministic (same skill output = same tool result).

See [skill-system.md](../skill-system.md) for how skills run in the background
and produce the data that query tools consume.

---

## What we skip (and why)

### LangGraph framework

PostHog themselves recommend against it. Their two-node graph (ROOT,
ROOT_TOOLS with a path_map of two entries) is structurally a while loop.
We use an actual while loop.

### Graph-based state machines

The `StateGraph`, `CompiledStateGraph`, conditional edges, and path maps
add indirection without adding capability for our use case. PostHog
needs them for mode switching across Analytics/SQL/Replay. We have two
modes with identical loop structure -- only the tool set and prompt
differ.

### Subagents

PostHog's own codebase warns against them: "Subgraphs incorrectly merge
messages, so please don't use them here." We use a single loop with full
context each turn. No context loss at transitions.

### LangGraph checkpointing

PostHog uses `DjangoCheckpointer` (~300 lines) for LangGraph state
serialization across page reloads. We persist conversation state with
standard Django models: `Conversation` tracks the session (mode, status,
title) and `ChatMessage` stores each turn (role, content, tool calls).
Messages are saved on every turn, so conversations survive page reloads
and can be resumed later via the stream endpoint.

### Other PostHog infrastructure we skip

- **Title generation subgraph** -- extension chat doesn't need conversation titles

---

## Implementation notes

### File locations

```
backend/
  services/
    ai_chat/
      agent.py          # run_agent_loop() - the while loop (runs inside Temporal activity)
      context.py         # build_system_prompt() - context injection
      modes.py           # Mode dataclass, MODES registry
      stream_events.py   # StreamEvent, StreamEventType
      stream.py          # StreamWriter, StreamReader (Redis Streams)
      tools/
        base.py          # PreplyTool ABC, QueryRunner
        query_errors.py  # QueryErrorsTool
        query_themes.py  # QueryThemesTool
        query_level.py   # QueryLevelTool
        ...
  views/
    ai_chat.py           # SSE endpoint, starts Temporal workflow, reads Redis stream
```

### Mode switching

The frontend sends `mode` in the chat request. The backend looks it up
in `MODES` and passes it to `run_agent_loop()`. No router, no state
machine -- the mode is a parameter.

### Error handling

We borrow PostHog's error categorization but simplify: catch
provider-specific client errors (e.g. `BadRequestError`), transient API
errors (rate limits, timeouts), and use `MAX_ITERATIONS` to prevent
runaway loops.

### Key differences from PostHog

1. **Direct SDK** instead of LangGraph -- one dependency, no framework lock-in
2. **While loop** instead of graph -- same semantics, 10x less code
3. **Mode as parameter** instead of mode manager class hierarchy
4. **Conversation + ChatMessage models** instead of Django checkpointer
5. **Temporal + Redis + SSE** (same as Medallion's pattern)
6. **Flat tool dispatch** instead of node path + context manager delegation

The pattern is the same: call LLM, check for tool_use, execute tools,
loop back. The implementation strips away everything that exists to serve
LangGraph rather than the product.
