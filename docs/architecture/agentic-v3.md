# Agentic v3 — Tool-First, Plan-First, Verified Multi-Agent Platform

> **Status:** PHASE 1 IN PROGRESS. This is a continuous refactor — the
> vision here is the end-state. Phases below show incremental delivery.

## Vision

Every response is the result of **reasoning → planning → tool execution →
observation → validation → synthesis**, not text generation. The system
behaves as an autonomous professional team (Planner / Coordinator /
Worker / Validator) rather than a chatbot.

**Non-negotiable rules:**

- Tools are the source of truth. Never invent workspace information.
- Every task produces a Plan before any tool call.
- After every tool call, the agent reflects: enough? need more? retry?
- Every observation is validated before synthesis.
- Workers plan and execute multi-step. They do not answer in one line.
- Multi-agent collaboration is preferred over a single all-knowing agent.

## Current vs. target

| Capability | Current (post v2) | Target (v3) |
|---|---|---|
| Planning | Hidden, ad-hoc per agent | Explicit `Plan` produced by Planner |
| Tool selection | Per-agent static list in `tool_mappings.py` | Dynamic via `ToolRegistry.list_by_capability()` |
| Multi-step tool use | LLM often stops after 1 call | Reflection loop forces "enough?" check |
| Tool discovery | LLM doesn't know what tools exist | `discover_tools_tool` queries registry at runtime |
| Verification | None | `Validator` checks observation before synthesis |
| Retry on tool failure | Error returned to LLM, no retry | `RetryEngine` with backoff + alt-tool fallback |
| Execution trace | `on_event` events only | Persisted `ExecutionTrace` (intent → plan → tools → obs → validations → synthesis) |
| Memory layers | One flat `dashboard_chat.json` | Conversation / workspace / long-term / trace |
| Approval for destructive ops | None | Permission system + human-in-the-loop checkpoint |
| Failure recovery | LLM handles ad-hoc | Structured: retry → alt tool → escalate to user |

## Architecture

```
User prompt
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  Planner (LLM call)                                     │
│  Produces: Plan(intent, complexity, subtasks[],         │
│           success_criteria, fallback_strategy)          │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  Coordinator                                            │
│  - For each subtask in Plan:                            │
│    - Dispatch to Worker (specialist or NEXUS)            │
│    - Stream events (plan / tool_call / observation /     │
│      validation / subtask_done)                         │
│    - On retry: RetryEngine picks alt tool                │
│  - Synthesize final response from observations           │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  Worker (specialist / NEXUS)                            │
│  1. PLAN: load ToolRegistry for capability, pick tools  │
│  2. ACT: call tool                                      │
│  3. OBSERVE: receive observation                         │
│  4. REFLECT: enough? need more? retry with diff params?  │
│  5. VERIFY: Validator sanity-checks observation          │
│  6. RETURN: structured SubTaskResult(observation, valid)  │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  ToolRegistry (shared)                                  │
│  - Catalog: every tool with name, description,           │
│    capabilities, requires_approval, owner_agent          │
│  - discover_tools_tool: agents query at runtime          │
│  - list_by_capability("crm") -> [Contact Info, ...]      │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  RetryEngine (shared)                                   │
│  - Transient failures (timeout, rate limit): backoff     │
│  - Permanent failures: try alt tool from registry        │
│  - After MAX_ATTEMPTS: escalate to user                  │
└────────────────────────────────────────────────────────┘
```

## ExecutionTrace schema

```python
class ExecutionTrace:
    trace_id: str                          # UUID
    user_prompt: str                       # original input
    plan: Plan                            # produced by Planner
    started_at: datetime
    finished_at: Optional[datetime]
    status: Literal["pending", "running", "success", "partial", "failed", "halted"]
    subtask_traces: list[SubTaskTrace]    # one per Plan subtask
    observations: list[Observation]       # every tool call result
    validations: list[Validation]         # every check
    final_response: Optional[str]         # synthesized answer
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    retry_count: int
    notes: list[str]                       # e.g. "halted: approval required"
```

Each `SubTaskTrace` has: `subtask_id`, `agent_key`, `tools_used`,
`observations`, `validations`, `status`, `reflection_log` (the "did I
have enough? need more?" decisions).

## Phase 1 (this delivery) — Foundation

Concrete files / changes:

1. **`src/ai/agentic/plan.py`** — `Plan`, `SubTask`, `ToolHint` Pydantic
   models.
2. **`src/ai/agentic/trace.py`** — `ExecutionTrace`, `SubTaskTrace`,
   `Observation`, `Validation`, `ReflectionNote` Pydantic models.
3. **`src/ai/agentic/registry.py`** — `ToolRegistry` class: discoverable
   catalog of every tool with capabilities, owners, approval flags.
4. **`src/ai/agentic/planner.py`** — `Planner` class that calls the LLM
   to produce a `Plan` from user prompt + history + tool catalog.
5. **`src/ai/agentic/reflection.py`** — shared `REFLECTION_TEMPLATE` prepended
   to every specialist backstory (plan → act → observe → reflect → verify).
6. **`src/ai/agentic/retry.py`** — `RetryEngine` with backoff + alt-tool
   fallback (used by `InfinityLLMAdapter`).
7. **`src/ai/tools/tool_registry.py`** — `discover_tools_tool` exposed to
   agents so they can query the registry at runtime.
8. **`src/ai/agents/tool_mappings.py`** — updated to register every tool
   in the `ToolRegistry` with capabilities.
9. **`src/ai/crewai_adapter/llm_adapter.py`** — calls `RetryEngine` on
   tool failures; fires `validation` and `reflection` events.
10. **`src/ai/flows/task_execution_flow_v2.py`** — new flow that uses
    Planner + Coordinator + ExecutionTrace. `task_execution_flow.py` V1
    kept for backward compat.
11. **`src/ai/prompts/loader.py`** — every specialist gets the
    `REFLECTION_TEMPLATE` prepended.
12. **API** — `/api/chat/stream` streams `plan` / `observation` /
    `validation` events so the UI shows the trace.
13. **Tests** — full coverage of the above.

## Phase 2 — Worker autonomy + Validator + Failure recovery

- `Worker` class with explicit act→observe→reflect→replan loop.
- `Validator` with rule-based + LLM-based sanity checks (e.g. "if tool
  says 0 leads but history shows last 5 had leads, re-query with looser
  filter").
- `FailureRecovery`: structured escalation chain
  (retry → alt-tool → ask another agent → ask user).
- Persisted trace in DB (`execution_traces` table).

## Phase 3 — Memory + Approval

- Conversation / workspace / trace memory separated.
- `PermissionSystem`: `requires_approval=True` tools (e.g.
  `db_update_business_profile_tool`, `db_delete_product`) gate execution
  behind a human checkpoint via the chat stream (`approval_required`
  event → frontend shows Approve/Deny buttons).
- Long-term memory: agent learnings per org (what tools work for what
  intents, past failure modes).

## Phase 4 — Hardening

- Event bus (replaces ad-hoc `on_event` callbacks).
- Observability persistence (every trace goes to a queryable store).
- Multi-agent collaboration: Worker can `ask_agent(other_key, question)`
  via the registry, results merged into plan.
- Rate limiting per agent, per tool, per org.

---

## Open questions for the next phases

1. Should the Planner be a separate LLM call, or part of the existing
   Claudia call? (Current Phase 1: separate call. Trade-off: latency vs.
   explicit plan.)
2. Should destructive tools (delete, update sensitive data) be gated
   behind approval? (Phase 3, but flagging now.)
3. Should we persist `ExecutionTrace` to DB or just keep in-memory? (Phase 2.)
4. Should the ToolRegistry be the single source of truth (replacing
   `STATIC_TOOL_MAPPINGS`)? (Phase 1 keeps both — registry is metadata,
   mappings is "who gets what". Phase 2 unifies.)
