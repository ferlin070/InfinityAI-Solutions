"""Worker — executes one SubTask via a CrewAI specialist agent.

The Worker is a thin wrapper around the existing agent-building and
CrewAI-kickoff machinery (`build_crewai_agent`, `InfinityLLMAdapter`,
`Crew(...).kickoff()`). It emits `subtask_start` / `subtask_done` /
`tool_call` / `observation` events (via the shared `on_event` callback
passed to the LLM adapter) so the UI can render live progress.

Key difference from V1's `_run_specialist`: the Worker runs exactly one
SubTask, not an arbitrary assignment string. This makes the execution
boundary explicit — the Coordinator knows what was asked, what tools
were called, and what was returned.
"""

from dataclasses import dataclass, field
from typing import Optional

from crewai import Crew, Process, Task

from src.ai.agentic.plan import SubTask
from src.ai.agents.factory import build_crewai_agent
from src.ai.agents.registry import load_agent
from src.ai.crewai_adapter.callbacks import chain, structured_log_callback
from src.ai.crewai_adapter.llm_adapter import EventCallback, InfinityLLMAdapter
from src.ai.providers.registry import resolve_provider
from src.core.config import logger


@dataclass
class SubTaskResult:
    agent_key: str
    description: str
    result: str
    status: str = "success"  # "success" | "failed" | "skipped"
    artifacts: list[dict] = field(default_factory=list)
    speed: str = "0s"
    error: Optional[str] = None
    tool_call_count: int = 0


class Worker:
    """Executes one SubTask using the CrewAI agent registered for
    `subtask.agent_key`. Not reusable — create a new Worker per subtask."""

    def __init__(self, on_event: Optional[EventCallback] = None):
        self._on_event = on_event or (lambda event_type, payload: None)

    def execute(self, subtask: SubTask, model: str, org_id: Optional[str] = None) -> SubTaskResult:
        from datetime import datetime, timezone

        agent_key = subtask.agent_key
        self._on_event("subtask_start", {
            "subtask_id": subtask.id,
            "agent_key": agent_key,
            "description": subtask.description[:300],
        })

        try:
            config = load_agent(agent_key, org_id=org_id)
        except (ValueError, KeyError) as e:
            logger.error(f"Worker: unknown agent '{agent_key}': {e}")
            result = SubTaskResult(
                agent_key=agent_key,
                description=subtask.description,
                result="",
                status="failed",
                error=f"Agent '{agent_key}' not found in registry.",
            )
            self._on_event("subtask_done", {
                "subtask_id": subtask.id,
                "agent_key": agent_key,
                "status": "failed",
                "error": result.error,
            })
            return result

        captured: list[dict] = []
        artifacts: list[dict] = []

        try:
            provider = resolve_provider(config.provider, config.org_id)
        except Exception as e:
            logger.error(f"Worker: failed to resolve provider for '{agent_key}': {e}")
            return SubTaskResult(
                agent_key=agent_key,
                description=subtask.description,
                result="",
                status="failed",
                error=f"Provider resolution failed: {e}",
            )

        llm = InfinityLLMAdapter(
            provider=provider,
            model=model,
            agent_key=config.key,
            org_id=config.org_id,
            on_result=chain(structured_log_callback, lambda k, o, r: captured.append(r)),
            on_event=self._on_event,
        )

        agent = build_crewai_agent(config, llm=llm, artifact_collector=artifacts)

        task = Task(
            description=subtask.description,
            expected_output=subtask.success_criteria,
            agent=agent,
        )

        try:
            crew_output = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            ).kickoff()
        except Exception as e:
            logger.error(f"Worker: CrewAI execution failed for '{agent_key}': {e}", exc_info=True)
            return SubTaskResult(
                agent_key=agent_key,
                description=subtask.description,
                result="",
                status="failed",
                error=str(e),
            )

        duration_s = sum(
            r.get("duration_ms", 0) for r in captured
        ) / 1000.0 if captured else 0.0

        result_text = str(crew_output).strip()

        self._on_event("subtask_done", {
            "subtask_id": subtask.id,
            "agent_key": agent_key,
            "status": "success",
            "result_text": result_text[:2000],
            "speed": f"{duration_s:.2f}s",
            "artifacts": artifacts or [],
        })

        return SubTaskResult(
            agent_key=agent_key,
            description=subtask.description,
            result=result_text,
            status="success",
            artifacts=artifacts,
            speed=f"{duration_s:.2f}s",
            tool_call_count=len(captured),
        )
