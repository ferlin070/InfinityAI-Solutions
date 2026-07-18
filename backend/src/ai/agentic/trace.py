"""Pydantic models for the ExecutionTrace layer.

An `ExecutionTrace` is the persisted, queryable record of one
user-prompt -> final-response cycle. It captures the full "reasoning
chain" the system claimed it did, so we can:

- Debug failures (what was the plan? what tools were called? what
  observations came back? where did the reasoning go wrong?).
- Show the user a visible trace in the UI (plan / observation /
  validation events).
- Evaluate the system over time (which tools fail most? which
  subtasks need retries?).

Every model here is intentionally JSON-serializable so it can be
persisted as a row in an `execution_traces` table later (Phase 2) or
written to a JSON file in the meantime."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

from src.ai.agentic.plan import Plan, SubTask


# ─── Atomic units ──────────────────────────────────────────────────────────

class ReflectionNote(BaseModel):
    """One 'did I have enough? need more?' decision by a Worker after a
    tool call. Kept as a structured record so we can audit whether the
    reflection actually happened (and what it concluded)."""
    after_observation_id: str = Field(description="The observation this reflection is about")
    decision: Literal["enough", "need_more", "retry", "escalate", "halt"]
    reasoning: str = Field(description="Why this decision")
    next_action: Optional[str] = Field(default=None, description="If 'need_more' or 'retry', what the worker intends to do next")


class Observation(BaseModel):
    """The result of one tool call. Captures the tool name, args, and
    the result string (truncated for storage). Also tracks latency and
    retry count for observability."""
    id: str
    tool_name: str
    agent_key: str
    arguments: dict = Field(default_factory=dict)
    result: str = Field(default="", description="The tool's return value (truncated to a safe size)")
    success: bool = True
    error: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_ms: int = 0
    retry_count: int = 0
    notes: list[str] = Field(default_factory=list, description="E.g. 'fell back to alt tool after first failed'")


class Validation(BaseModel):
    """A check on an observation. Either rule-based (cheap, deterministic)
    or LLM-based (smarter but slower). Always records what was checked
    and whether it passed."""
    observation_id: str
    check: str = Field(description="What we validated, e.g. 'result is non-empty JSON' or 'result contains at least one lead'")
    passed: bool
    rationale: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# ─── SubTask-level trace ──────────────────────────────────────────────────

class SubTaskTrace(BaseModel):
    """Everything that happened while executing one SubTask: which
    agent, which tools, which observations, which validations, which
    reflection decisions, and the final status."""
    subtask: SubTask
    agent_key: str
    status: Literal["pending", "running", "success", "partial", "failed", "halted_approval"] = "pending"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    observations: list[Observation] = Field(default_factory=list)
    validations: list[Validation] = Field(default_factory=list)
    reflection_log: list[ReflectionNote] = Field(default_factory=list)
    final_result: Optional[str] = Field(default=None, description="The worker's final text/summary for this subtask")
    error: Optional[str] = None


# ─── Top-level trace ──────────────────────────────────────────────────────

class ExecutionTrace(BaseModel):
    """The full record of one user-prompt -> response cycle. One of
    these is produced for every `kickoff` of `TaskExecutionFlowV2`."""
    trace_id: str
    user_prompt: str
    conversation_history: list[dict] = Field(default_factory=list)
    plan: Optional[Plan] = None
    status: Literal["pending", "running", "success", "partial", "failed", "halted_approval", "halted_budget"] = "pending"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    subtask_traces: list[SubTaskTrace] = Field(default_factory=list)
    final_response: Optional[str] = None
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_tool_calls: int = 0
    retry_count: int = 0
    notes: list[str] = Field(default_factory=list)

    def tool_call_count(self) -> int:
        return sum(len(st.observations) for st in self.subtask_traces)

    def successful_subtasks(self) -> list[SubTaskTrace]:
        return [st for st in self.subtask_traces if st.status == "success"]

    def failed_subtasks(self) -> list[SubTaskTrace]:
        return [st for st in self.subtask_traces if st.status in ("failed", "partial")]
