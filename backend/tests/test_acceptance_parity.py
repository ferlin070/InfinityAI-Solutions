"""Step 8 acceptance test (docs/architecture/ai-execution-crewai.md §10): given
the same scripted LLM responses, TaskExecutionFlow (CrewAI + OpenAI) must produce
the same routing decisions, the same response envelope shape, and the same
edge-case handling as backend/src/services/orchestrator.py's execute_task() — the
code it replaces. Only the execution engine changed; behavior must not have.

DB-backed comparisons (agent_runs/executions rows) are out of scope — that
persistence layer is deferred pending a live Supabase project (§7).
"""
import asyncio
import sys
import os
from unittest.mock import patch

from fastapi import BackgroundTasks

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.flows.task_execution_flow import TaskExecutionFlow
from src.ai.providers.base import LLMResult
from src.schemas.models import UserInput
from src.services.orchestrator import execute_task


def _run_old_orchestrator(claudia_text: str, specialist_texts: list[str], prompt: str):
    """Drives the code being replaced, scripting src.services.llm.call_nvidia the
    same way ScriptedProvider scripts the new provider layer: call 1 = Claudia,
    calls 2..N = each specialist in assignment order."""
    queue = [claudia_text] + list(specialist_texts)

    def fake_call_nvidia(sys_prompt, user_prompt, model, temperature=0.7):
        text = queue.pop(0) if queue else "Selesai."
        return text, 0.15

    with patch("src.services.orchestrator.call_nvidia", side_effect=fake_call_nvidia), \
         patch("src.services.orchestrator.upload_to_drive"):
        return asyncio.run(
            execute_task(UserInput(prompt=prompt, model_name="meta/llama-3.1-70b-instruct"), BackgroundTasks())
        )


def _run_new_flow(claudia_text: str, specialist_texts: list[str], prompt: str):
    """Drives TaskExecutionFlow with the same scripted sequence via ScriptedProvider
    (see test_task_execution_flow.py) so both systems see identical 'LLM' output."""

    class ScriptedProvider:
        def __init__(self, texts):
            self._queue = list(texts)

        def complete(self, messages, model, temperature=0.7, max_tokens=4096):
            text = self._queue.pop(0) if self._queue else "Selesai."
            return LLMResult(
                text=text, tokens_in=10, tokens_out=5, cost_usd=0.001,
                duration_ms=150, model=model, provider="openai",
            )

    provider = ScriptedProvider([claudia_text] + list(specialist_texts))
    with patch("src.ai.agents.factory.resolve_provider", return_value=provider), \
         patch("src.ai.flows.task_execution_flow.resolve_provider", return_value=provider):
        flow = TaskExecutionFlow()
        return flow.kickoff(inputs={"prompt": prompt, "org_id": None, "model": "gpt-4o-mini"})


def test_parity_happy_path_single_specialist():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}'
    old = _run_old_orchestrator(claudia_json, ["Bajet bulan ini: RM5,000."], "Kira bajet pemasaran.")
    new = _run_new_flow(claudia_json, ["Bajet bulan ini: RM5,000."], "Kira bajet pemasaran.")

    assert old.status == new.status == "success"
    assert [r.agent for r in old.results] == [r.agent for r in new.results] == ["ZARA"]
    assert [r.result for r in old.results] == [r.result for r in new.results] == ["Bajet bulan ini: RM5,000."]


def test_parity_multiple_specialists_same_order():
    claudia_json = (
        '{"status": "accepted", "assignments": ['
        '{"agent": "ZARA", "task": "kira bajet"}, '
        '{"agent": "AIMAN", "task": "buat strategi iklan"}]}'
    )
    texts = ["Bajet: RM5,000.", "Strategi: FB Ads."]
    old = _run_old_orchestrator(claudia_json, texts, "Tolong bantu bajet dan iklan.")
    new = _run_new_flow(claudia_json, texts, "Tolong bantu bajet dan iklan.")

    assert old.status == new.status == "success"
    assert [r.agent for r in old.results] == [r.agent for r in new.results] == ["ZARA", "AIMAN"]


def test_parity_rejected_task():
    claudia_json = '{"status": "rejected", "reason": "Tugasan di luar bidang kuasa AI."}'
    old = _run_old_orchestrator(claudia_json, [], "Buat sesuatu yang pelik.")
    new = _run_new_flow(claudia_json, [], "Buat sesuatu yang pelik.")

    assert old.status == new.status == "rejected"
    assert old.message == new.message == "Tugasan di luar bidang kuasa AI."


def test_parity_claudia_replies_without_json():
    text = "Maaf, saya tidak faham arahan ini."
    old = _run_old_orchestrator(text, [], "???")
    new = _run_new_flow(text, [], "???")

    assert old.status == new.status == "error"
    assert old.message == new.message == "Claudia membalas tanpa JSON sah."


def test_parity_unknown_agent_is_skipped_not_fatal():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "NOBODY", "task": "x"}]}'
    old = _run_old_orchestrator(claudia_json, [], "tugasan pelik")
    new = _run_new_flow(claudia_json, [], "tugasan pelik")

    assert old.status == new.status == "success"
    assert old.results == new.results == []


def test_parity_no_assignments_is_an_error():
    claudia_json = '{"status": "accepted", "assignments": []}'
    old = _run_old_orchestrator(claudia_json, [], "tugasan kosong")
    new = _run_new_flow(claudia_json, [], "tugasan kosong")

    assert old.status == new.status == "error"
    assert old.message == new.message == "Claudia tidak memberikan tugasan kepada sesiapa."
