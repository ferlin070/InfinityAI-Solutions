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
