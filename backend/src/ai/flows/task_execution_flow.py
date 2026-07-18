import json
import re
import time
from typing import Callable

from crewai import Crew, Process, Task
from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field

from src.ai.agents.factory import build_crewai_agent
from src.ai.agents.registry import load_agent
from src.ai.crewai_adapter.callbacks import chain, structured_log_callback
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
from src.ai.providers.base import LLMResult
from src.ai.providers.errors import ProviderError
from src.ai.providers.registry import resolve_provider
from src.core.config import logger
from src.core.constants import SPECIALIST_AGENTS
from src.schemas.models import AgentResult, ExecuteResponse
from src.services.logging import extract_json

EventCallback = Callable[[str, dict], None]


def _check_usage_budget(org_id: str | None) -> bool:
    """Per-org usage/budget guard (docs/architecture/ai-execution-crewai.md §5.2
    guardrail #4: halt before overspend, notify the owner). MVP has no
    `organizations`/`agent_runs` DB table yet (§4/§7 deferred pending a real
    Supabase project), so this always allows execution. Once that table exists,
    this function is the only place that needs to change — `execute_specialists`
    below already calls it before every specialist execution.
    """
    return True


class TaskExecutionState(BaseModel):
    org_id: str | None = None
    model: str = "gpt-4o-mini"
    prompt: str = ""
    history: list[dict] = Field(default_factory=list)
    status: str = "running"
    assignments: list[dict] = Field(default_factory=list)
    results: list[AgentResult] = Field(default_factory=list)
    rejection_reason: str | None = None
    chat_reply: str | None = None
    error: str | None = None
    started_at: float = 0.0


class TaskExecutionFlow(Flow[TaskExecutionState]):
    """CrewAI-native replacement for backend/src/services/orchestrator.py's
    execute_task(). Same two-step deterministic pattern as the orchestrator it
    replaces — Claudia classifies via strict JSON, then only the assigned
    specialists run — now expressed as explicit Flow steps so guardrails sit
    between steps instead of inside one opaque function.
    See docs/architecture/ai-execution-crewai.md §3.2 for the step diagram.

    `on_event` is an optional progress callback (agent_key/tool/status style
    dict payloads) used to stream live activity to a caller (see
    backend/src/api/routes.py's /api/chat/stream) — it never affects the
    deterministic result, only observability of it.
    """

    def __init__(self, on_event: EventCallback | None = None):
        super().__init__()
        self._on_event = on_event or (lambda event_type, payload: None)

    @start()
    def classify_intent(self) -> ExecuteResponse | None:
        self.state.started_at = time.time()
        self._on_event("status", {"text": "Claudia sedang menganalisis arahan..."})

        claudia_config = load_agent("CLAUDIA", org_id=self.state.org_id)
        claudia_agent = build_crewai_agent(
            claudia_config, on_result=structured_log_callback, on_event=self._on_event
        )

        task = Task(
            description=f"{self._format_history()}Mesej terbaru Bos: {self.state.prompt}",
            expected_output=(
                "JSON tepat mengikut format yang dinyatakan dalam backstory anda. "
                "Tiada teks lain di luar JSON."
            ),
            agent=claudia_agent,
        )

        try:
            crew_output = Crew(
                agents=[claudia_agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
            ).kickoff()
        except ProviderError as e:
            logger.error(f"Ralat provider semasa Claudia memproses tugasan: {e}", exc_info=True)
            self.state.status = "error"
            self.state.error = "Ralat dalaman semasa berhubung dengan penyedia AI."
            return self._build_response()

        raw_text = str(crew_output).strip()
        json_str = extract_json(raw_text)

        if not json_str:
            # The LLM gave a non-empty answer but it wasn't parseable
            # as the strict routing JSON. Don't treat this as a fatal
            # error — the user got a real answer and the agentic-v3
            # rewrite already says "call tools first, reply naturally".
            # Fall back to `chat` status with the raw text as the
            # reply so the user still sees Claudia's response. A
            # warning is logged so we can spot the prompt gap.
            if raw_text:
                logger.warning(
                    "Claudia replied without parseable routing JSON; "
                    "treating as chat. First 200 chars: %r", raw_text[:200],
                )
                self.state.status = "chat"
                self.state.chat_reply = raw_text[:4000]
                return self._build_response()
            # Truly empty response — that's a real error.
            logger.warning("Claudia membalas kosong (tiada JSON, tiada teks).")
            self.state.status = "error"
            self.state.error = "Claudia membalas tanpa JSON sah."
            return self._build_response()

        decision = self._parse_decision(json_str)
        if decision is None:
            # JSON extracted but didn't match any known shape. The
            # `chat` branch is the most forgiving — fall through.
            logger.warning(
                "Claudia JSON parsed but did not match a known routing "
                "shape. First 200 chars: %r", json_str[:200],
            )
            self.state.status = "chat"
            self.state.chat_reply = json_str[:4000]
            return self._build_response()

        decision_status = decision.get("status")

        if decision_status == "chat":
            self.state.status = "chat"
            self.state.chat_reply = decision.get("reply", "Baik, boleh awak jelaskan lagi?")
            return self._build_response()

        if decision_status == "rejected":
            self.state.status = "rejected"
            self.state.rejection_reason = decision.get("reason", "Tugasan di luar bidang kuasa AI.")
            return self._build_response()

        assignments = decision.get("assignments", [])
        if not assignments:
            self.state.status = "error"
            self.state.error = "Claudia tidak memberikan tugasan kepada sesiapa."
            return self._build_response()

        agent_names = ", ".join((a.get("agent") or "?") for a in assignments)
        self._on_event("status", {"text": f"Menghantar tugasan kepada {agent_names}..."})

        # Emit a structured `plan` event so the Agent Workspace UI can
        # show the user what the planner is about to do BEFORE execution
        # starts. Even though V1 doesn't use the formal Planner module
        # yet, the assignments are themselves a plan — the user can
        # inspect and the UI can render them as a step.
        self._on_event("plan", {
            "intent": self.state.prompt[:200],
            "complexity": "simple" if len(assignments) == 1 else ("moderate" if len(assignments) <= 3 else "complex"),
            "subtasks": [
                {
                    "id": f"sub_{i+1}",
                    "description": (a.get("task") or "")[:300],
                    "agent_key": (a.get("agent") or "").upper(),
                    "success_criteria": "Selesaikan tugasan dan pulangkan hasil.",
                    "required_capabilities": [],
                    "depends_on": [],
                    "parallelizable": False,
                    "approval_required": False,
                    "max_tool_calls": 10,
                }
                for i, a in enumerate(assignments)
            ],
            "success_criteria": "Berikan jawapan / hasil untuk permintaan Bos.",
        })

        self.state.assignments = assignments
        return None  # not terminal yet — execute_specialists continues the flow

    @listen(classify_intent)
    def execute_specialists(self, classify_result: ExecuteResponse | None) -> ExecuteResponse:
        if classify_result is not None:
            return classify_result  # classify_intent already reached a terminal state

        for i, assignment in enumerate(self.state.assignments):
            agent_key = (assignment.get("agent") or "").upper()
            task_text = assignment.get("task", "")
            subtask_id = f"sub_{i+1}"

            if agent_key not in SPECIALIST_AGENTS:
                logger.warning(f"Claudia assigned unknown agent '{agent_key}', skipping.")
                continue

            # Emit subtask_start so the UI can open a new timeline step
            # for this specialist.
            self._on_event("subtask_start", {
                "subtask_id": subtask_id,
                "agent_key": agent_key,
                "description": task_text[:300],
            })

            if not _check_usage_budget(self.state.org_id):
                self.state.status = "halted_budget"
                self.state.error = "Had penggunaan AI bulanan telah dicapai."
                return self._build_response()

            self._on_event("agent_start", {"agent": agent_key})
            try:
                result = self._run_specialist(agent_key, task_text)
            except ProviderError as e:
                logger.error(f"Ralat provider semasa '{agent_key}' memproses tugasan: {e}", exc_info=True)
                self._on_event("subtask_done", {
                    "subtask_id": subtask_id,
                    "agent_key": agent_key,
                    "status": "failed",
                    "error": "Ralat dalaman sistem semasa memproses tugasan.",
                })
                self.state.status = "error"
                self.state.error = "Ralat dalaman sistem semasa memproses tugasan."
                return self._build_response()
            self._on_event("agent_done", {"agent": agent_key})
            # Emit subtask_done with the worker's final result so the
            # Agent Workspace UI can render the completed step.
            self._on_event("subtask_done", {
                "subtask_id": subtask_id,
                "agent_key": agent_key,
                "status": "success",
                "result_text": (result.result or "")[:2000],
                "speed": result.speed,
                "artifacts": result.artifacts or [],
            })

            self.state.results.append(result)

        self.state.status = "success"
        return self._build_response()

    def _run_specialist(self, agent_key: str, task_text: str) -> AgentResult:
        config = load_agent(agent_key, org_id=self.state.org_id)
        captured: list[LLMResult] = []
        artifacts: list[dict] = []
        provider = resolve_provider(config.provider, config.org_id)
        llm = InfinityLLMAdapter(
            provider=provider,
            model=config.model,
            agent_key=config.key,
            org_id=config.org_id,
            on_result=chain(structured_log_callback, lambda k, o, r: captured.append(r)),
            on_event=self._on_event,
        )
        agent = build_crewai_agent(config, llm=llm, artifact_collector=artifacts)
        task = Task(
            description=task_text,
            expected_output="Hasil kerja dalam teks biasa.",
            agent=agent,
        )

        crew_output = Crew(
            agents=[agent], tasks=[task], process=Process.sequential, verbose=False
        ).kickoff()

        duration_s = (captured[-1]["duration_ms"] / 1000) if captured else 0.0
        return AgentResult(
            agent=agent_key,
            task=task_text,
            result=str(crew_output),
            speed=f"{duration_s:.2f}s",
            artifacts=artifacts or None,
        )

    def _format_history(self) -> str:
        if not self.state.history:
            return ""
        lines = [
            f"[{m.get('role', 'user')}]: {m.get('content', '')}"
            for m in self.state.history[-20:]
        ]
        return "Sejarah perbualan lepas:\n" + "\n".join(lines) + "\n\n"

    def _build_response(self) -> ExecuteResponse:
        total_speed = f"{time.time() - self.state.started_at:.2f}s"
        if self.state.status == "success":
            return ExecuteResponse(
                status="success",
                results=self.state.results,
                total_speed=total_speed,
                model=self.state.model,
            )
        if self.state.status == "chat":
            return ExecuteResponse(status="chat", message=self.state.chat_reply, model=self.state.model)
        if self.state.status == "rejected":
            return ExecuteResponse(
                status="rejected", message=self.state.rejection_reason, model=self.state.model
            )
        return ExecuteResponse(status="error", message=self.state.error, model=self.state.model)

    @staticmethod
    def _parse_decision(json_str: str) -> dict | None:
        """Mirrors the JSON/regex-fallback parsing already used by
        backend/src/services/orchestrator.py, unchanged, so Claudia's routing
        behavior is identical to today's — only the execution engine around it
        changed."""
        try:
            cleaned = "".join(ch for ch in json_str if ch.isprintable() or ch in "\n\r\t")
            cleaned = cleaned.replace("\n", "\\n").replace("\r", "\\r")
            return json.loads(cleaned)
        except Exception:
            try:
                status_match = re.search(r'"status":\s*"(\w+)"', json_str)
                status = status_match.group(1) if status_match else "error"

                if status == "chat":
                    reply_match = re.search(r'"reply":\s*"(.*?)"', json_str, re.DOTALL)
                    reply = reply_match.group(1) if reply_match else "Baik, boleh awak jelaskan lagi?"
                    return {"status": "chat", "reply": reply}

                if status == "rejected":
                    reason_match = re.search(r'"reason":\s*"(.*?)"', json_str, re.DOTALL)
                    reason = reason_match.group(1) if reason_match else "Tugas ditolak."
                    return {"status": "rejected", "reason": reason}

                assignments = []
                agents = re.findall(r'"agent":\s*"(\w+)"', json_str)
                tasks = re.findall(r'"task":\s*"(.*?)"', json_str, re.DOTALL)
                for a, t in zip(agents, tasks):
                    assignments.append({"agent": a, "task": t})
                return {"status": "accepted", "assignments": assignments}
            except Exception as e:
                logger.error(f"Kegagalan total menghurai JSON dari Claudia: {str(e)}")
                return None
