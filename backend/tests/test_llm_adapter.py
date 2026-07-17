import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.crewai_adapter.callbacks import chain, structured_log_callback
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
from src.ai.providers.base import LLMResult


def _fake_provider(text="hasil"):
    provider = MagicMock()
    provider.complete.return_value = LLMResult(
        text=text,
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        duration_ms=250,
        model="gpt-4o-mini",
        provider="openai",
    )
    return provider


def test_call_with_string_wraps_as_user_message():
    provider = _fake_provider()
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="ZARA")

    response = adapter.call("kira bajet bulan ini")

    assert response == "hasil"
    provider.complete.assert_called_once()
    kwargs = provider.complete.call_args.kwargs
    assert kwargs["messages"] == [{"role": "user", "content": "kira bajet bulan ini"}]
    assert kwargs["model"] == "gpt-4o-mini"


def test_call_with_message_list_passes_through():
    provider = _fake_provider()
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="CLAUDIA")
    messages = [
        {"role": "system", "content": "Anda Claudia"},
        {"role": "user", "content": "tugasan"},
    ]

    adapter.call(messages)

    assert provider.complete.call_args.kwargs["messages"] == messages


def test_call_invokes_on_result_callback():
    provider = _fake_provider()
    seen = []
    adapter = InfinityLLMAdapter(
        provider=provider,
        model="gpt-4o-mini",
        agent_key="ZARA",
        org_id="org-1",
        on_result=lambda agent_key, org_id, result: seen.append((agent_key, org_id, result)),
    )

    adapter.call("hi")

    assert len(seen) == 1
    assert seen[0][0] == "ZARA"
    assert seen[0][1] == "org-1"
    assert seen[0][2]["text"] == "hasil"


def test_call_with_tools_passes_tools_to_provider():
    provider = _fake_provider()
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="ZARA")

    tools = [{"type": "function", "function": {"name": "lookup_price", "parameters": {"type": "object"}}}]
    adapter.call("hi", tools=tools)

    provider.complete.assert_called_once()
    assert provider.complete.call_args.kwargs["tools"] == tools


def test_supports_function_calling_is_true():
    adapter = InfinityLLMAdapter(provider=_fake_provider(), model="gpt-4o-mini", agent_key="ZARA")
    assert adapter.supports_function_calling() is True


def test_context_window_known_and_unknown_model():
    known = InfinityLLMAdapter(provider=_fake_provider(), model="gpt-4o-mini", agent_key="ZARA")
    unknown = InfinityLLMAdapter(provider=_fake_provider(), model="some-future-model", agent_key="ZARA")

    assert known.get_context_window_size() == 128_000
    assert unknown.get_context_window_size() == 128_000  # falls back to conservative default


def test_chain_runs_all_callbacks_even_if_one_fails():
    calls = []

    def ok_callback(agent_key, org_id, result):
        calls.append("ok")

    def broken_callback(agent_key, org_id, result):
        raise RuntimeError("boom")

    combined = chain(broken_callback, ok_callback)
    combined("ZARA", "org-1", _fake_provider().complete.return_value)

    assert calls == ["ok"]


def test_on_event_fires_around_tool_call_execution():
    provider = MagicMock()
    provider.complete.side_effect = [
        LLMResult(
            text="", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
            tool_calls=[{"id": "call_1", "function": {"name": "my_tool", "arguments": "{}"}}],
        ),
        LLMResult(
            text="hasil akhir", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
        ),
    ]
    events = []
    adapter = InfinityLLMAdapter(
        provider=provider,
        model="gpt-4o-mini",
        agent_key="DANISH",
        on_event=lambda event_type, payload: events.append((event_type, payload)),
    )

    response = adapter.call(
        "buat banner",
        tools=[{"type": "function", "function": {"name": "my_tool"}}],
        available_functions={"my_tool": lambda: "tool output"},
    )

    assert response == "hasil akhir"
    assert events == [
        ("tool_call", {"agent": "DANISH", "tool": "my_tool", "status": "start"}),
        ("tool_call", {"agent": "DANISH", "tool": "my_tool", "status": "done"}),
    ]


def test_on_event_fires_done_even_when_tool_raises():
    provider = MagicMock()
    provider.complete.side_effect = [
        LLMResult(
            text="", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
            tool_calls=[{"id": "call_1", "function": {"name": "broken_tool", "arguments": "{}"}}],
        ),
        LLMResult(
            text="dah selesai", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
        ),
    ]
    events = []

    def _boom():
        raise RuntimeError("boom")

    adapter = InfinityLLMAdapter(
        provider=provider,
        model="gpt-4o-mini",
        agent_key="DANISH",
        on_event=lambda event_type, payload: events.append((event_type, payload)),
    )

    adapter.call(
        "buat banner",
        tools=[{"type": "function", "function": {"name": "broken_tool"}}],
        available_functions={"broken_tool": _boom},
    )

    assert [e[1]["status"] for e in events] == ["start", "done"]


def test_structured_log_callback_does_not_raise():
    result = LLMResult(
        text="x", tokens_in=1, tokens_out=1, cost_usd=0.0, duration_ms=1,
        model="gpt-4o-mini", provider="openai",
    )
    structured_log_callback("ZARA", "org-1", result)
