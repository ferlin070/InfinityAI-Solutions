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

    def complete(self, messages, model, temperature=0.7, max_tokens=4096, tools=None):
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


def _run_flow(provider, prompt="Kira bajet pemasaran bulan ini.", on_event=None, history=None):
    with patch("src.ai.agents.factory.resolve_provider", return_value=provider), \
         patch("src.ai.flows.task_execution_flow.resolve_provider", return_value=provider):
        flow = TaskExecutionFlow(on_event=on_event)
        inputs = {"prompt": prompt, "org_id": None, "model": "gpt-4o-mini"}
        if history is not None:
            inputs["history"] = history
        return flow.kickoff(inputs=inputs)


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


def test_chat_status_replies_without_routing_to_a_specialist():
    claudia_json = '{"status": "chat", "reply": "Hai Bos! Ada apa yang saya boleh bantu?"}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])

    response = _run_flow(provider, prompt="hai")

    assert response.status == "chat"
    assert response.message == "Hai Bos! Ada apa yang saya boleh bantu?"
    assert provider.call_count == 1  # only Claudia ran, no specialist invoked


def test_chat_status_missing_reply_falls_back_to_clarifying_question():
    claudia_json = '{"status": "chat"}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])

    response = _run_flow(provider, prompt="???")

    assert response.status == "chat"
    assert response.message == "Baik, boleh awak jelaskan lagi?"


def test_parse_decision_chat_json_path():
    decision = TaskExecutionFlow._parse_decision('{"status": "chat", "reply": "Hai!"}')
    assert decision == {"status": "chat", "reply": "Hai!"}


def test_parse_decision_chat_regex_fallback_on_malformed_json():
    malformed = '{"status": "chat", "reply": "Boleh jelaskan lagi tak" trailing garbage}'
    decision = TaskExecutionFlow._parse_decision(malformed)

    assert decision["status"] == "chat"
    assert decision["reply"] == "Boleh jelaskan lagi tak"


def test_format_history_produces_readable_transcript():
    flow = TaskExecutionFlow()
    flow.state.history = [
        {"role": "user", "content": "Nama saya Bos"},
        {"role": "assistant", "content": "Baik Bos!"},
    ]

    formatted = flow._format_history()

    assert "Nama saya Bos" in formatted
    assert "Baik Bos!" in formatted


def test_format_history_empty_when_no_history():
    flow = TaskExecutionFlow()
    assert flow._format_history() == ""


def test_on_event_reports_status_and_agent_lifecycle():
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}'
    provider = ScriptedProvider(scripted_texts=[claudia_json, "Bajet: RM5,000."])
    events = []

    _run_flow(provider, on_event=lambda event_type, payload: events.append((event_type, payload)))

    event_types = [e[0] for e in events]
    assert "status" in event_types
    assert ("agent_start", {"agent": "ZARA"}) in events
    assert ("agent_done", {"agent": "ZARA"}) in events


def test_danish_actually_generates_an_image_end_to_end():
    """Regression test for the exact bug seen live in production: Danish had
    the Image Generation tool attached, but CrewAI's executor never passes
    `tools`/`available_functions` to InfinityLLMAdapter.call() (see
    llm_adapter.py's `_build_tool_schema` fix) — so the tool was never invoked
    and Danish just wrote banner *copy* text instead of generating an image.
    Drives the real CrewAI Agent/Task/Crew/Flow machinery end-to-end (only the
    OpenAI provider and the image tool's OpenAI client are mocked), so this
    would have caught that bug."""
    from unittest.mock import MagicMock
    claudia_json = '{"status": "accepted", "assignments": [{"agent": "DANISH", "task": "buat banner goreng pisang cheese"}]}'

    class ToolCallingProvider:
        def __init__(self):
            self.call_count = 0

        def complete(self, messages, model, temperature=0.7, max_tokens=4096, tools=None):
            self.call_count += 1
            if self.call_count == 1:
                return LLMResult(
                    text=claudia_json, tokens_in=10, tokens_out=5, cost_usd=0.001,
                    duration_ms=100, model=model, provider="openai",
                )
            if self.call_count == 2:
                assert tools, "Danish's tools must have been auto-built and offered to the model"
                tool_name = tools[0]["function"]["name"]
                return LLMResult(
                    text="", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
                    model=model, provider="openai",
                    tool_calls=[{
                        "id": "call_1",
                        "function": {"name": tool_name, "arguments": '{"prompt": "banner goreng pisang cheese"}'},
                    }],
                )
            return LLMResult(
                text="Ini banner untuk goreng pisang cheese anda!", tokens_in=10, tokens_out=5,
                cost_usd=0.001, duration_ms=100, model=model, provider="openai",
            )

    fake_openai_client = MagicMock()
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(b64_json="ZmFrZWltYWdl")]
    fake_openai_client.images.generate.return_value = fake_resp

    with patch("src.ai.tools.image_generation.OpenAI", return_value=fake_openai_client):
        response = _run_flow(ToolCallingProvider(), prompt="buat banner goreng pisang cheese")

    assert response.status == "success"
    result = response.results[0]
    assert result.agent == "DANISH"
    assert result.artifacts == [{
        "type": "image",
        "mime_type": "image/png",
        "data_base64": "ZmFrZWltYWdl",
        "caption": "banner goreng pisang cheese",
    }]


def test_on_event_not_fired_for_specialists_when_task_rejected():
    claudia_json = '{"status": "rejected", "reason": "Di luar bidang."}'
    provider = ScriptedProvider(scripted_texts=[claudia_json])
    events = []

    _run_flow(provider, on_event=lambda event_type, payload: events.append((event_type, payload)))

    assert all(e[0] != "agent_start" for e in events)
