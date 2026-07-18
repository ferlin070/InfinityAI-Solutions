"""Coordinator — walks a Plan and dispatches subtasks to Workers.

The Coordinator is the main execution loop for the agentic-v3 architecture.
Given a `Plan` (produced by the `Planner`), it:

1. Emits the plan as a `plan` event so the UI shows the user what's coming.
2. Iterates through subtasks in dependency order (via `Plan.ready_subtasks()`).
3. For each subtask:
   a. If `approval_required=True`, pauses and requests human approval via
      the `ApprovalManager`.
   b. Dispatches subtask to a `Worker` (CrewAI agent execution).
   c. Records the result and updates the trace.
4. After all subtasks complete (or fail), emits a `final` event and returns
   the aggregated result.

Threading model:
  - The Coordinator itself is synchronous and blocking. It runs in the
    background thread created by `chat_stream` in `routes.py`.
  - Approval pauses block the background thread on a `threading.Event`.
    The approval POST handler (FastAPI main thread) resolves the event,
    unblocking the Coordinator.
"""

import time
from typing import Optional

from src.ai.agentic.approval import create_approval, wait_for_approval
from src.ai.agentic.plan import Plan, SubTask
from src.ai.agentic.trace import ExecutionTrace, SubTaskTrace, Observation, Validation, ReflectionNote
from src.ai.agentic.worker import SubTaskResult, Worker
from src.ai.crewai_adapter.llm_adapter import EventCallback
from src.core.config import logger


class Coordinator:
    """One Coordinator per user request. Execute once; not reusable."""

    def __init__(
        self,
        plan: Plan,
        on_event: Optional[EventCallback] = None,
        model: str = "gpt-4o-mini",
        org_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        self.plan = plan
        self._on_event = on_event or (lambda t, p: None)
        self._model = model
        self._org_id = org_id
        self._conversation_id = conversation_id or "default"
        self._started_at = 0.0
        self._completed_ids: set[str] = set()
        self._subtask_results: list[SubTaskResult] = []

    def execute(self) -> list[SubTaskResult]:
        """Walk the plan, execute ready subtasks, return results.

        Returns a list of per-subtask results in execution order.
        If a subtask fails or is skipped, the coordinator continues
        with the next ready subtask."""
        self._started_at = time.time()
        self._emit_plan()

        while len(self._completed_ids) < len(self.plan.subtasks):
            ready = self.plan.ready_subtasks(self._completed_ids)
            if not ready:
                logger.warning(
                    f"Coordinator: stalled — {len(self.plan.subtasks)} total, "
                    f"{len(self._completed_ids)} completed, 0 ready."
                )
                break

            for st in ready:
                result = self._dispatch(st)
                self._completed_ids.add(st.id)
                self._subtask_results.append(result)

        return self._subtask_results

    # ── Internal ───────────────────────────────────────────────────────────

    def _emit_plan(self):
        self._on_event("plan", {
            "intent": self.plan.intent,
            "complexity": self.plan.complexity,
            "success_criteria": self.plan.success_criteria,
            "subtasks": [
                {
                    "id": st.id,
                    "description": st.description[:300],
                    "agent_key": st.agent_key,
                    "success_criteria": st.success_criteria,
                    "required_capabilities": st.required_capabilities,
                    "depends_on": st.depends_on,
                    "parallelizable": st.parallelizable,
                    "approval_required": st.approval_required,
                    "max_tool_calls": st.max_tool_calls,
                }
                for st in self.plan.subtasks
            ],
        })

    def _dispatch(self, subtask: SubTask) -> SubTaskResult:
        if subtask.approval_required:
            approved = self._request_approval(subtask)
            if not approved:
                logger.info(f"Coordinator: subtask '{subtask.id}' skipped (approval rejected)")
                return SubTaskResult(
                    agent_key=subtask.agent_key,
                    description=subtask.description,
                    result="",
                    status="skipped",
                )

        worker = Worker(on_event=self._on_event)
        result = worker.execute(subtask, model=self._model, org_id=self._org_id)
        return result

    def _request_approval(self, subtask: SubTask) -> bool:
        approval_id = create_approval()
        self._on_event("approval_required", {
            "approval_id": approval_id,
            "subtask_id": subtask.id,
            "agent_key": subtask.agent_key,
            "description": subtask.description[:500],
            "tool_hints": [h.tool_name for h in subtask.tool_hints],
        })

        decision = wait_for_approval(approval_id)
        if decision is None:
            logger.warning(f"Coordinator: approval '{approval_id}' returned None (timeout)")
            return False
        return bool(decision.get("approved", False))
