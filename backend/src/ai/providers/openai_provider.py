import time
from typing import Iterator

import openai
from openai import OpenAI

from src.ai.providers.base import LLMProvider, LLMResult, Message
from src.ai.providers.errors import (
    ProviderAuthError,
    ProviderContextLengthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.config import logger

# USD per 1K tokens. Update when OpenAI changes pricing; a model missing here still
# works, it just records cost_usd=0.0 (logged) instead of blocking execution.
_PRICING_PER_1K_TOKENS = {
    "gpt-4o": {"in": 0.0025, "out": 0.01},
    "gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
    "gpt-4.1": {"in": 0.002, "out": 0.008},
    "gpt-4.1-mini": {"in": 0.0004, "out": 0.0016},
    "gpt-4.1-nano": {"in": 0.0001, "out": 0.0004},
    "o3-mini": {"in": 0.0011, "out": 0.0044},
}


class OpenAIProvider(LLMProvider):
    """The only provider for MVP. Wraps the OpenAI SDK — nothing outside this module
    imports `openai` directly (docs/architecture/ai-execution-crewai.md §4)."""

    def __init__(self, api_key: str, timeout: float = 60.0):
        self._client = OpenAI(api_key=api_key or "missing_key", timeout=timeout)

    def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResult:
        start = time.time()
        try:
            resp = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise self._normalize_error(e) from e

        duration_ms = int((time.time() - start) * 1000)
        usage = resp.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        return LLMResult(
            text=resp.choices[0].message.content or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider="openai",
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

    @staticmethod
    def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
        rates = _PRICING_PER_1K_TOKENS.get(model)
        if rates is None:
            logger.warning(f"No pricing entry for OpenAI model '{model}' — cost_usd recorded as 0.0")
            return 0.0
        return round((tokens_in / 1000) * rates["in"] + (tokens_out / 1000) * rates["out"], 6)
