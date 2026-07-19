import sys
import os
from unittest.mock import MagicMock, patch

import openai
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.providers.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.ai.providers.openai_provider import OpenAIProvider


def _fake_response(text="hello", tokens_in=10, tokens_out=5):
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=text))]
    resp.usage = MagicMock(prompt_tokens=tokens_in, completion_tokens=tokens_out)
    return resp


def test_complete_returns_llm_result_with_known_pricing():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = _fake_response(
        text="hasil", tokens_in=1000, tokens_out=1000
    )

    result = provider.complete(
        messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini"
    )

    assert result["text"] == "hasil"
    assert result["tokens_in"] == 1000
    assert result["tokens_out"] == 1000
    assert result["provider"] == "openai"
    assert result["model"] == "gpt-4o-mini"
    # gpt-4o-mini: 0.00015 in + 0.0006 out per 1K tokens, 1K tokens each side
    assert result["cost_usd"] == pytest.approx(0.00015 + 0.0006)


def test_complete_unknown_model_costs_zero_but_does_not_fail():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = _fake_response()

    result = provider.complete(
        messages=[{"role": "user", "content": "hi"}], model="some-future-model"
    )

    assert result["cost_usd"] == 0.0


def test_complete_normalizes_auth_error():
    provider = OpenAIProvider(api_key="bad-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.side_effect = openai.AuthenticationError(
        "invalid key", response=MagicMock(status_code=401), body=None
    )

    with pytest.raises(ProviderAuthError):
        provider.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")


def test_complete_normalizes_rate_limit_error():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.side_effect = openai.RateLimitError(
        "rate limited", response=MagicMock(status_code=429), body=None
    )

    with pytest.raises(ProviderRateLimitError):
        provider.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")


def test_complete_normalizes_unknown_error_to_provider_error():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.side_effect = ValueError("boom")

    with pytest.raises(ProviderError):
        provider.complete(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")


def test_stream_yields_text_chunks():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="hel"))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="lo"))]
    provider._client.chat.completions.create.return_value = [chunk1, chunk2]

    chunks = list(
        provider.stream(messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini")
    )

    assert chunks == ["hel", "lo"]


def _content_chunk(text):
    chunk = MagicMock()
    chunk.usage = None
    chunk.choices = [MagicMock(delta=MagicMock(content=text, tool_calls=None))]
    return chunk


def _final_usage_chunk(tokens_in, tokens_out):
    chunk = MagicMock()
    chunk.usage = MagicMock(prompt_tokens=tokens_in, completion_tokens=tokens_out)
    chunk.choices = []
    return chunk


def _tool_call_delta_chunk(index, id_=None, fn_name=None, arguments=None):
    tc = MagicMock()
    tc.index = index
    tc.id = id_
    if fn_name is not None or arguments is not None:
        fn = MagicMock()
        # NOTE: MagicMock(name=...) sets the mock's own debug repr, not a
        # `.name` attribute — must assign it after construction instead.
        fn.name = fn_name
        fn.arguments = arguments
        tc.function = fn
    else:
        tc.function = None
    chunk = MagicMock()
    chunk.usage = None
    chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=[tc]))]
    return chunk


def test_stream_complete_streams_text_and_reports_deltas():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = [
        _content_chunk("hel"),
        _content_chunk("lo"),
        _final_usage_chunk(10, 5),
    ]

    seen = []
    result = provider.stream_complete(
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-4o-mini",
        on_delta=seen.append,
    )

    assert seen == ["hel", "lo"]
    assert result["text"] == "hello"
    assert result["tokens_in"] == 10
    assert result["tokens_out"] == 5
    assert result["tool_calls"] is None


def test_stream_complete_accumulates_fragmented_tool_call_deltas():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    # Real OpenAI streams send the tool name in one chunk and the JSON
    # arguments spread across several — this must merge them by index.
    provider._client.chat.completions.create.return_value = [
        _tool_call_delta_chunk(0, id_="call_1", fn_name="Get_Weather", arguments=""),
        _tool_call_delta_chunk(0, arguments='{"city":'),
        _tool_call_delta_chunk(0, arguments='"KL"}'),
        _final_usage_chunk(20, 8),
    ]

    result = provider.stream_complete(
        messages=[{"role": "user", "content": "hi"}], model="gpt-4o-mini"
    )

    assert result["text"] == ""
    assert result["tool_calls"] == [
        {"id": "call_1", "function": {"name": "Get_Weather", "arguments": '{"city":"KL"}'}}
    ]


def test_stream_complete_raises_interrupted_error_when_cancelled_before_call():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()

    with pytest.raises(InterruptedError):
        provider.stream_complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
            should_stop=lambda: True,
        )
    provider._client.chat.completions.create.assert_not_called()


def test_stream_complete_raises_interrupted_error_mid_stream():
    provider = OpenAIProvider(api_key="test-key")
    provider._client = MagicMock()
    provider._client.chat.completions.create.return_value = [
        _content_chunk("hel"),
        _content_chunk("lo"),
        _final_usage_chunk(10, 5),
    ]

    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        # Let the first chunk through, cancel before the second.
        return calls["n"] > 1

    with pytest.raises(InterruptedError):
        provider.stream_complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o-mini",
            should_stop=should_stop,
        )
