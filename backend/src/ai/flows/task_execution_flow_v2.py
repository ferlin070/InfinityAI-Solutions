"""V2 execution flow — Planner → Coordinator → Worker → response.

Replaces the V1 flow (Claudia-based routing) with the agentic-v3
pipeline: the Planner analyses the prompt and produces a structured
Plan, the Coordinator walks the plan and dispatches subtasks, and
the Worker executes each subtask via a CrewAI specialist agent.

Fallback behaviour:
  - If the Planner returns the NEXUS fallback (simple plan, one
    subtask, NEXUS agent), the V2 flow still executes it — the
    Coordinator sends the task to the NEXUS generalist, which has
    the union of all tools plus browser/MCP. This is strictly more
    capable than V1's "reply as chat" fallback.
  - If the Coordinator encounters an execution error on every
    subtask, the flow returns a chat-style error message instead
    of a raw exception.
"""

from typing import Optional

from src.ai.agentic.approval import list_pending
from src.ai.agentic.coordinator import Coordinator
from src.ai.agentic.planner import Planner
from src.ai.crewai_adapter.llm_adapter import EventCallback
from src.core.config import logger
from src.schemas.models import AgentResult, ExecuteResponse


class TaskExecutionFlowV2:
    """Planner + Coordinator orchestration for the agentic-v3 pipeline.

    Constructed per user request. Call `run()` exactly once and use
    the returned `ExecuteResponse`.
    """

    def __init__(self, on_event: Optional[EventCallback] = None):
        self._on_event = on_event or (lambda event_type, payload: None)

    def run(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        history: Optional[list[dict]] = None,
        org_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> ExecuteResponse:
        history = history or []

        self._on_event("status", {"text": "Planner sedang menganalisis arahan..."})

        # 1. Plan
        planner = Planner(model=model)
        plan = planner.plan(user_prompt=prompt, history=history)

        if not plan.subtasks:
            logger.warning("V2 flow: Planner returned empty plan, falling back to chat.")
            return ExecuteResponse(
                status="chat",
                message=(
                    "Saya tidak dapat merancang tindakan untuk permintaan ini. "
                    "Boleh awak jelaskan lagi?"
                ),
                model=model,
            )

        # 2. Execute
        coordinator = Coordinator(
            plan=plan,
            on_event=self._on_event,
            model=model,
            org_id=org_id,
            conversation_id=conversation_id,
        )

        results = coordinator.execute()

        # 3. Build response
        if not results:
            return ExecuteResponse(
                status="error",
                message="Tiada subtask berjaya dilaksanakan.",
                model=model,
            )

        agent_results = []
        all_failed = True
        for r in results:
            if r.status == "success":
                all_failed = False
            agent_results.append(AgentResult(
                agent=r.agent_key,
                task=r.description[:500],
                result=r.result[:4000] if r.result else "",
                speed=r.speed,
                artifacts=r.artifacts or [],
            ))

        if all_failed:
            # Every subtask failed — return as chat with a summary
            error_details = "; ".join(
                f"{r.agent_key}: {r.error or 'gagal'}" for r in results if r.error
            )
            return ExecuteResponse(
                status="chat",
                message=f"Maaf, semua ejen gagal melaksanakan tugasan. ({error_details})",
                model=model,
            )

        return ExecuteResponse(
            status="success",
            results=agent_results,
            total_speed="",
            model=model,
        )
