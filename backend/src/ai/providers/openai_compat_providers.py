"""OpenAI-compatible provider base for any vendor that speaks the OpenAI Chat
Completions API. Concrete subclasses only override `provider_name`, the default
`base_url`, and which env var to read for the API key.

Vendors covered here:
- OpenRouter (`https://openrouter.ai/api/v1`) — multi-model proxy.
- Ollama (`http://localhost:11434/v1`) — local models, no API key required.
- Azure OpenAI — uses your deployment URL + API key.

If your vendor is not OpenAI-compatible, write a new file next to this one
implementing `LLMProvider` directly (see anthropic_provider.py / gemini_provider.py).
"""

import time
from typing import Iterator

import openai
from openai import OpenAI

from src.ai.providers.base import LLMProvider, LLMResult, Message, ToolCall
from src.ai.providers.errors import (
    ProviderAuthError,
    ProviderContextLengthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.config import logger


class OpenAICompatibleProvider(LLMProvider):
    """Reusable OpenAI-compatible provider. Subclasses set provider_name,
    default_base_url, default_api_key_env, and an optional pricing map."""

    provider_name: str = "openai_compat"
    default_base_url: str | None = None
    default_api_key_env: str = "OPENAI_API_KEY"
    default_api_key: str = ""
    pricing: dict[str, dict[str, float]] = {}

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        self._client = OpenAI(
            api_key=api_key or "missing_key",
            base_url=base_url or self.default_base_url,
            timeout=timeout,
        )

    def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        start = time.time()
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if tools:
                kwargs["tools"] = tools
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise self._normalize_error(e) from e

        duration_ms = int((time.time() - start) * 1000)
        usage = resp.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        choice = resp.choices[0].message

        tool_calls = None
        if choice.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    function={"name": tc.function.name, "arguments": tc.function.arguments},
                )
                for tc in choice.tool_calls
            ]

        return LLMResult(
            text=choice.content or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider=self.provider_name,
            tool_calls=tool_calls,
        )

    def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        try:
            chunks = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in chunks:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise self._normalize_error(e) from e

    @staticmethod
    def _normalize_error(e: Exception) -> ProviderError:
        if isinstance(e, openai.AuthenticationError):
            return ProviderAuthError(str(e))
        if isinstance(e, openai.RateLimitError):
            return ProviderRateLimitError(str(e))
        if isinstance(e, openai.APITimeoutError):
            return ProviderTimeoutError(str(e))
        if isinstance(e, openai.BadRequestError) and "context length" in str(e).lower():
            return ProviderContextLengthError(str(e))
        return ProviderError(str(e))

    def _estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        rates = self.pricing.get(model)
        if rates is None:
            logger.warning(
                f"No pricing entry for {self.provider_name} model '{model}' — cost_usd=0.0"
            )
            return 0.0
        return round(
            (tokens_in / 1000) * rates["in"] + (tokens_out / 1000) * rates["out"], 6
        )


# ─── OpenRouter ────────────────────────────────────────────────────────────────

class OpenRouterProvider(OpenAICompatibleProvider):
    provider_name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"
    default_api_key_env = "OPENROUTER_API_KEY"
    default_api_key = ""
    # Indicative pricing in USD per 1K tokens — pick a representative model per
    # family; missing entries fall through to cost_usd=0.0.
    pricing = {
        "anthropic/claude-sonnet-4-5": {"in": 0.003, "out": 0.015},
        "anthropic/claude-3.5-sonnet": {"in": 0.003, "out": 0.015},
        "openai/gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
        "openai/gpt-4o": {"in": 0.0025, "out": 0.01},
        "google/gemini-2.5-flash": {"in": 0.0003, "out": 0.0025},
        "meta-llama/llama-3.1-70b-instruct": {"in": 0.00059, "out": 0.00079},
        "qwen/qwen-2.5-72b-instruct": {"in": 0.0004, "out": 0.0004},
    }


# ─── Ollama (local) ────────────────────────────────────────────────────────────

class OllamaProvider(OpenAICompatibleProvider):
    provider_name = "ollama"
    default_base_url = "http://localhost:11434/v1"
    default_api_key_env = "OLLAMA_API_KEY"
    default_api_key = "ollama"  # Ollama ignores the value but OpenAI SDK requires one
    # Local models are free at runtime — recorded as 0.0.
    pricing = {}


# ─── Azure OpenAI ──────────────────────────────────────────────────────────────

class AzureOpenAIProvider(OpenAICompatibleProvider):
    provider_name = "azure"
    default_base_url = None
    default_api_key_env = "AZURE_OPENAI_API_KEY"
    default_api_key = ""
    # Azure reuses the same model pricing as OpenAI in most cases; map by
    # deployment name or model id.
    pricing = {
        "gpt-4o": {"in": 0.0025, "out": 0.01},
        "gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
        "gpt-4.1": {"in": 0.002, "out": 0.008},
        "gpt-4.1-mini": {"in": 0.0004, "out": 0.0016},
    }
