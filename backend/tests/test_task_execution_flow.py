import sys
import os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.flows.task_execution_flow import TaskExecutionFlow, TaskExecutionState
from src.ai.providers.base import LLMResult
from src.ai.providers.errors import ProviderError


class ScriptedProvider:
    """Stands in for OpenAIProvider. Returns scripted text in call order — call 1
    is always Claudia's classification, calls 2..N are each assigned specialist's
    task, in assignment order. Drives the real crewai.Agent/Task/Crew/Flow
    machinery end-to-end; nothing about CrewAI itself is mocked."""

    def __init__(self, scripted_texts: list[str] | None = None, raise_from_call: int | None = None):
        self._queue = list(scripted_texts or [])
        self._raise_from_call = raise_from_call
        self.call_count = 0

    def complete(self, messages, model, temperature=0.7, max_tokens=4096):
        self.call_count += 1
        if self._raise_from_call is not None and self.call_count >= self._raise_from_call:
            # CrewAI's own Agent executor retries a failing LLM call up to
            # `max_retry_limit` (default 2) before re-raising — see
            # crewai/agent.py execute_task(). Only a *persistent* failure
            # (every call from this point on raises) reaches our except
            # ProviderError; a single transient failure gets silently retried.
            raise ProviderError("simulated persistent provider failure")
        text = self._queue.pop(0) if self._queue else "Selesai."
        return LLMResult(
            text=text, tokens_in=10, tokens_out=5, cost_usd=0.001,
            duration_ms=150, model=model, provider="openai",
        )


def _run_flow(provider, prompt="Kira bajet pemasaran bulan ini."):
    with patch("src.ai.agents.factory.resolve_provider", return_value=provider), \
         patch("src.ai.flows.task_execution_flow.resolve_provider", return_value=provider):
        flow = TaskExecutionFlow()
        return flow.kickoff(inputs={"prompt": prompt, "org_id": None, "model": "gpt-4o-mini"})


def test_happy_path_single_specialist():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}'
    provider = ScriptedProvider(scripted_texts=[claudia_json, "Bajet bulan ini: RM5,000."])

    response = _run_flow(provider)

    assert response.status == "success"
    assert len(response.results) == 1
    assert response.results[0].agent == "ZARA"
    assert response.results[0].result == "Bajet bulan ini: RM5,000."
    assert provider.call_count == 2


def test_happy_path_multiple_specialists():
    claudia_json = (
        '{"status": "accepted", "assignments": ['
        '{"agent": "ZARA", "task": "kira bajet"}, '
        '{"agent": "AIMAN", "task": "buat strategi iklan"}]}'
    )
    provider = ScriptedProvider(scripted_texts=[claudia_json, "Bajet: RM5,000.", "Strategi: FB Ads."])

    response = _run_flow(provider)

    assert response.status == "success"
    assert [r.agent for r in response.results] == ["ZARA", "AIMAN"]
    assert provider.call_count == 3


def test_rejected_task():
    claudia_json = '{"status": "rejected", "reason": "Tugasan di luar bidang kuasa AI."}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])

    response = _run_flow(provider)

    assert response.status == "rejected"
    assert response.message == "Tugasan di luar bidang kuasa AI."
    assert provider.call_count == 1


def test_claudia_replies_without_json():
    provider = ScriptedProvider(scripted_texts=["Maaf, saya tidak faham."])

    response = _run_flow(provider)

    assert response.status == "error"
    assert response.message == "Claudia membalas tanpa JSON sah."


def test_claudia_provider_error_becomes_generic_error():
    provider = ScriptedProvider(raise_from_call=1)

    response = _run_flow(provider)

    assert response.status == "error"
    assert response.message == "Ralat dalaman semasa berhubung dengan penyedia AI."
    # initial attempt + max_retry_limit(2) retries, all persistently failing
    assert provider.call_count == 3


def test_specialist_provider_error_becomes_generic_error():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}'
    provider = ScriptedProvider(scripted_texts=[claudia_json], raise_from_call=2)

    response = _run_flow(provider)

    assert response.status == "error"
    assert response.message == "Ralat dalaman sistem semasa memproses tugasan."


def test_unknown_agent_in_assignment_is_skipped_not_fatal():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "NOBODY", "task": "x"}]}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])

    response = _run_flow(provider)

    assert response.status == "success"
    assert response.results == []


def test_no_assignments_is_an_error():
    claudia_json = '{"status": "accepted", "assignments": []}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])

    response = _run_flow(provider)

    assert response.status == "error"
    assert response.message == "Claudia tidak memberikan tugasan kepada sesiapa."
