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


def test_call_with_tools_raises_not_implemented():
    provider = _fake_provider()
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="ZARA")

    with pytest.raises(NotImplementedError):
        adapter.call("hi", tools=[{"name": "lookup_price"}])

    provider.complete.assert_not_called()


def test_supports_function_calling_is_false():
    adapter = InfinityLLMAdapter(provider=_fake_provider(), model="gpt-4o-mini", agent_key="ZARA")
    assert adapter.supports_function_calling() is False


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


def test_structured_log_callback_does_not_raise():
    result = LLMResult(
        text="x", tokens_in=1, tokens_out=1, cost_usd=0.0, duration_ms=1,
        model="gpt-4o-mini", provider="openai",
    )
    structured_log_callback("ZARA", "org-1", result)
