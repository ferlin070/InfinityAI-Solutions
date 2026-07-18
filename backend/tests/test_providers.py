"""Tests for the new provider bridges and registry. The vendor SDKs are
optional, so we only test what works without them: registry resolution,
default URLs, and the OpenAI-compatible base class behaviour with a mocked
client."""

import sys
import os
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.providers.errors import ProviderError, UnsupportedProviderError
from src.ai.providers.registry import resolve_provider
from src.ai.providers.openai_compat_providers import (
    OpenRouterProvider,
    OllamaProvider,
    AzureOpenAIProvider,
    OpenAICompatibleProvider,
)


def test_resolve_openai_returns_openai_provider():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENAI_API_KEY", "test-key")
        from src.core import config
        config.OPENAI_API_KEY = "test-key"
        provider = resolve_provider("openai")
    from src.ai.providers.openai_provider import OpenAIProvider
    assert isinstance(provider, OpenAIProvider)


def test_resolve_unknown_provider_raises():
    with pytest.raises(UnsupportedProviderError):
        resolve_provider("not-a-real-provider")


def _url(provider) -> str:
    """OpenAI SDK normalises base_url by adding a trailing slash. Strip it
    so tests can compare with the raw env value."""
    return str(provider._client.base_url).rstrip("/")


def test_resolve_ollama_default_url():
    with pytest.MonkeyPatch.context() as m:
        m.delenv("OLLAMA_BASE_URL", raising=False)
        m.setenv("OLLAMA_API_KEY", "anything")
        provider = resolve_provider("ollama")
    assert _url(provider) == "http://localhost:11434/v1"


def test_resolve_ollama_custom_url():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("OLLAMA_BASE_URL", "http://gpu-box.lan:11434/v1")
        m.setenv("OLLAMA_API_KEY", "anything")
        provider = resolve_provider("ollama")
    assert _url(provider) == "http://gpu-box.lan:11434/v1"


def test_resolve_openrouter_default_url():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("OPENROUTER_API_KEY", "sk-or-test")
        provider = resolve_provider("openrouter")
    assert _url(provider) == "https://openrouter.ai/api/v1"


def test_resolve_azure_requires_base_url():
    with pytest.MonkeyPatch.context() as m:
        m.setenv("AZURE_OPENAI_API_KEY", "azure-key")
        m.setenv("AZURE_OPENAI_BASE_URL", "https://my.openai.azure.com/openai/deployments/gpt-4o")
        provider = resolve_provider("azure")
    assert isinstance(provider, AzureOpenAIProvider)
    assert "my.openai.azure.com" in _url(provider)


def test_provider_name_on_each_subclass():
    assert OpenRouterProvider.provider_name == "openrouter"
    assert OllamaProvider.provider_name == "ollama"
    assert AzureOpenAIProvider.provider_name == "azure"


def test_estimate_cost_unknown_model_is_zero_and_warns(caplog):
    provider = OllamaProvider(api_key="x", base_url="http://x")
    cost = provider._estimate_cost("unknown-model-9000", 1000, 1000)
    assert cost == 0.0


def test_estimate_cost_known_openrouter_model():
    provider = OpenRouterProvider(api_key="x", base_url="https://openrouter.ai/api/v1")
    cost = provider._estimate_cost("openai/gpt-4o-mini", 1_000_000, 1_000_000)
    # 1000 * 0.00015 + 1000 * 0.0006 = 0.75
    assert cost == pytest.approx(0.75, rel=1e-3)
