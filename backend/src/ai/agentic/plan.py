"""Pydantic models for the Plan / SubTask layer of the agentic v3
architecture.

A `Plan` is produced by the `Planner` (LLM call) before any tool is
invoked. The `Coordinator` then walks the plan and dispatches each
`SubTask` to the right Worker.

This is the structured replacement for the implicit "LLM chains of
thought" that the current `TaskExecutionFlow` relies on. Making the
plan explicit means:
- The user can SEE the plan in the UI before execution starts.
- The Coordinator can reason about parallelism, dependencies, retries.
- Tests can pin the planner's behaviour without running the LLM.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ToolHint(BaseModel):
    """A planner's guess at which tools a subtask will need. The actual
    Worker may use more (or fewer) — this is a hint, not a contract.
    Kept short so the plan stays readable in the UI."""

    tool_name: str = Field(description="Tool name as it appears in the ToolRegistry, e.g. 'DB List Leads'")
    reason: str = Field(description="Why the planner thinks this tool is needed for this subtask")


class SubTask(BaseModel):
    """One unit of work in a Plan. Always has a clear success criterion
    and (if needed) explicit dependencies on other subtasks."""

    id: str = Field(description="Stable identifier within the plan, e.g. 'sub_1'")
    description: str = Field(description="What the worker should accomplish, in plain language")
    agent_key: str = Field(description="Which agent should handle this (MAYA, HAKIM, NEXUS, etc.)")
    success_criteria: str = Field(description="How the worker knows it's done. E.g. 'return N leads grouped by score'")
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Capability tags the worker must have. Planner can match these against ToolRegistry.",
    )
    tool_hints: list[ToolHint] = Field(
        default_factory=list,
        description="Tools the planner thinks the worker will need. Hint only — the worker decides.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Other subtask IDs that must complete successfully before this one starts.",
    )
    parallelizable: bool = Field(
        default=False,
        description="If True, the Coordinator may run this in parallel with other parallelizable subtasks that share no dependencies.",
    )
    approval_required: bool = Field(
        default=False,
        description="If True, this subtask is a destructive op (delete, update sensitive data) and the Coordinator will halt and request human approval before execution.",
    )
    max_tool_calls: int = Field(
        default=10,
        description="Soft cap on tool calls for this subtask. The Worker will stop and reflect after this many.",
    )


class Plan(BaseModel):
    """The full execution plan produced by the Planner. The Coordinator
    walks `subtasks` in dependency order, parallelising where possible."""

    intent: str = Field(description="What the user actually wants, in one sentence. Restated by the planner so we can spot misunderstanding.")
    complexity: Literal["simple", "moderate", "complex"] = Field(
        description="Planner's assessment. 'simple' = 1 subtask, 1-2 tool calls. 'moderate' = 2-3 subtasks. 'complex' = 4+ subtasks or cross-domain.",
    )
    subtasks: list[SubTask] = Field(
        default_factory=list,
        description="The work to be done, in execution order. May be reordered by Coordinator based on dependencies.",
    )
    success_criteria: str = Field(
        description="What 'success' means for the WHOLE plan. E.g. 'return a 3-sentence summary of platform status'.",
    )
    fallback_strategy: Optional[str] = Field(
        default=None,
        description="If the plan fails, what should the Coordinator do? E.g. 'fall back to chat reply with the partial observations'.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Anything the planner wants the Coordinator to know — assumptions, risks, edge cases.",
    )

    def subtask_by_id(self, subtask_id: str) -> Optional[SubTask]:
        for st in self.subtasks:
            if st.id == subtask_id:
                return st
        return None

    def ready_subtasks(self, completed_ids: set[str]) -> list[SubTask]:
        """Subtasks whose dependencies are all completed (or have no deps)."""
        ready = []
        for st in self.subtasks:
            if st.id in completed_ids:
                continue
            if all(dep in completed_ids for dep in st.depends_on):
                ready.append(st)
        return ready
