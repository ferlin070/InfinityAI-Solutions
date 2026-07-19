import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.crewai_adapter.callbacks import chain, structured_log_callback
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
from src.ai.providers.base import LLMResult


def _fake_provider(text="hasil"):
    # A bare MagicMock() provider's `.stream_complete` has no default body,
    # so tests must configure it directly (return_value/side_effect) — the
    # adapter calls `stream_complete`, not `complete`, so mocking `complete`
    # here would silently no-op and hang the tool-calling loop (an
    # unconfigured `stream_complete()` returns a MagicMock, whose `.get()`
    # and truthiness checks are always truthy, so `while True` never exits).
    provider = MagicMock()
    provider.stream_complete.return_value = LLMResult(
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
    provider.stream_complete.assert_called_once()
    kwargs = provider.stream_complete.call_args.kwargs
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

    assert provider.stream_complete.call_args.kwargs["messages"] == messages


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

    provider.stream_complete.assert_called_once()
    assert provider.stream_complete.call_args.kwargs["tools"] == tools


def test_call_streams_text_deltas_as_token_events():
    """The adapter must call stream_complete with an on_delta callback and
    fire a `token` SSE event per chunk (this is what makes the Agent
    Workspace UI render text as it arrives instead of all at once)."""
    provider = MagicMock()

    def fake_stream_complete(messages, model, temperature, max_tokens, tools, on_delta, should_stop):
        if on_delta:
            on_delta("hel")
            on_delta("lo")
        return LLMResult(
            text="hello", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
        )

    provider.stream_complete.side_effect = fake_stream_complete
    events = []
    adapter = InfinityLLMAdapter(
        provider=provider, model="gpt-4o-mini", agent_key="ZARA",
        on_event=lambda t, p: events.append((t, p)),
    )

    response = adapter.call("hi")

    assert response == "hello"
    assert events == [
        ("token", {"agent": "ZARA", "delta": "hel"}),
        ("token", {"agent": "ZARA", "delta": "lo"}),
    ]


def test_call_does_not_emit_token_events_for_planner():
    """PLANNER only ever produces routing JSON, not user-facing prose —
    streaming its raw partial JSON into the chat timeline would just be
    noise, so it's excluded from `token` events."""
    provider = MagicMock()

    def fake_stream_complete(messages, model, temperature, max_tokens, tools, on_delta, should_stop):
        if on_delta:
            on_delta('{"intent"')
        return LLMResult(
            text='{"intent": "x"}', tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
        )

    provider.stream_complete.side_effect = fake_stream_complete
    events = []
    adapter = InfinityLLMAdapter(
        provider=provider, model="gpt-4o-mini", agent_key="PLANNER",
        on_event=lambda t, p: events.append((t, p)),
    )

    adapter.call("plan this")

    assert events == []


def test_call_raises_interrupted_error_when_cancelled_before_call():
    provider = _fake_provider()
    adapter = InfinityLLMAdapter(
        provider=provider, model="gpt-4o-mini", agent_key="ZARA",
        should_stop=lambda: True,
    )

    with pytest.raises(InterruptedError):
        adapter.call("hi")
    provider.stream_complete.assert_not_called()


def test_call_passes_should_stop_through_to_provider():
    provider = _fake_provider()
    should_stop = lambda: False
    adapter = InfinityLLMAdapter(
        provider=provider, model="gpt-4o-mini", agent_key="ZARA", should_stop=should_stop,
    )

    adapter.call("hi")

    assert provider.stream_complete.call_args.kwargs["should_stop"] is should_stop


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
    combined("ZARA", "org-1", _fake_provider().stream_complete.return_value)

    assert calls == ["ok"]


def test_on_event_fires_around_tool_call_execution():
    provider = MagicMock()
    provider.stream_complete.side_effect = [
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
    # `observation` event was added in agentic-v3 (Phase 1) so the Agent
    # Workspace UI can render a full ToolExecutionCard with the result.
    event_types = [e[0] for e in events]
    assert ("tool_call", {"agent": "DANISH", "tool": "my_tool", "status": "start"}) in events
    assert ("tool_call", {"agent": "DANISH", "tool": "my_tool", "status": "done"}) in events
    assert "observation" in event_types
    # The observation should carry the tool's actual result.
    obs = next(e for e in events if e[0] == "observation")
    assert obs[1]["tool"] == "my_tool"
    assert obs[1]["agent"] == "DANISH"
    assert "tool output" in obs[1]["result"]
    assert obs[1]["success"] is True


def test_on_event_fires_done_even_when_tool_raises():
    provider = MagicMock()
    provider.stream_complete.side_effect = [
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

    # Both the start + done events must still fire even when the tool
    # raises. agentic-v3 also fires an `observation` with success=False.
    event_types = [e[0] for e in events]
    statuses = [e[1]["status"] for e in events if e[0] == "tool_call"]
    assert statuses == ["start", "done"]
    assert "observation" in event_types
    obs = next(e for e in events if e[0] == "observation")
    assert obs[1]["success"] is False
    assert "Error" in obs[1]["result"]


def test_build_tool_schema_sanitizes_names_and_extracts_json_schema():
    from crewai.tools import tool

    @tool("My Cool Tool")
    def my_tool(x: str) -> str:
        """Does a thing with x."""
        return f"did {x}"

    schema, available_functions = InfinityLLMAdapter._build_tool_schema([my_tool])

    assert schema == [{
        "type": "function",
        "function": {
            "name": "My_Cool_Tool",  # OpenAI rejects spaces in function names
            "description": my_tool.description,
            "parameters": my_tool.args_schema.model_json_schema(),
        },
    }]
    assert available_functions["My_Cool_Tool"](x="hi") == "did hi"


def test_call_auto_builds_tools_from_from_task_when_crewai_omits_them():
    """Regression test for the real production bug: CrewAI's own executor
    (crew_agent_executor.py's get_llm_response) never passes `tools`/
    `available_functions`/`from_agent` to a custom BaseLLM.call() — only
    `from_task`. Confirmed live: an agent with a real tool attached (Danish +
    Image Generation) never actually invoked it; it just wrote text describing
    what the image would look like. If this auto-build path breaks again, tool
    use silently degrades back to that exact failure mode."""
    from crewai.tools import tool

    @tool("Stub Tool")
    def stub_tool(prompt: str) -> str:
        """A stub tool for testing."""
        return f"stub result for {prompt}"

    provider = MagicMock()
    provider.stream_complete.side_effect = [
        LLMResult(
            text="", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
            tool_calls=[{"id": "call_1", "function": {"name": "Stub_Tool", "arguments": '{"prompt": "banner"}'}}],
        ),
        LLMResult(
            text="Ini banner anda!", tokens_in=10, tokens_out=5, cost_usd=0.001, duration_ms=100,
            model="gpt-4o-mini", provider="openai",
        ),
    ]
    fake_task = MagicMock()
    fake_task.tools = [stub_tool]
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="DANISH")

    response = adapter.call("buat banner", from_task=fake_task)

    assert response == "Ini banner anda!"
    # The auto-built tools schema must have reached the provider on the first call.
    first_call_tools = provider.stream_complete.call_args_list[0].kwargs["tools"]
    assert first_call_tools[0]["function"]["name"] == "Stub_Tool"
    # And the tool result must have been fed back as a tool message.
    second_call_messages = provider.stream_complete.call_args_list[1].kwargs["messages"]
    assert any(m.get("content") == "stub result for banner" for m in second_call_messages)


def test_call_does_not_auto_build_tools_when_explicitly_provided():
    provider = _fake_provider()
    fake_task = MagicMock()
    fake_task.tools = [MagicMock(name="should not be used")]
    adapter = InfinityLLMAdapter(provider=provider, model="gpt-4o-mini", agent_key="ZARA")

    adapter.call("hi", tools=[{"type": "function", "function": {"name": "explicit"}}], from_task=fake_task)

    assert provider.stream_complete.call_args.kwargs["tools"] == [
        {"type": "function", "function": {"name": "explicit"}}
    ]


def test_structured_log_callback_does_not_raise():
    result = LLMResult(
        text="x", tokens_in=1, tokens_out=1, cost_usd=0.0, duration_ms=1,
        model="gpt-4o-mini", provider="openai",
    )
    structured_log_callback("ZARA", "org-1", result)
