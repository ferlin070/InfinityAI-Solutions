import time
from typing import Callable, Iterator

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
                ToolCall(id=tc.id, function={"name": tc.function.name, "arguments": tc.function.arguments})
                for tc in choice.tool_calls
            ]

        return LLMResult(
            text=choice.content or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider="openai",
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

    def stream_complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
        on_delta: "Callable[[str], None] | None" = None,
        should_stop: "Callable[[], bool] | None" = None,
    ) -> LLMResult:
        """Real token-level streaming, including tool-call support — OpenAI
        sends tool calls as index-keyed partial deltas across many chunks
        (id/name/arguments each arrive fragmented), so this accumulates them
        by index before turning them into the same `ToolCall` shape
        `complete()` returns. `stream_options={"include_usage": True}` asks
        for a final usage-only chunk so cost/token accounting stays accurate
        even though we never call the non-streaming endpoint."""
        if should_stop and should_stop():
            raise InterruptedError("cancelled before request was sent")

        start = time.time()
        stream_ctx = None
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            if tools:
                kwargs["tools"] = tools
            stream_ctx = self._client.chat.completions.create(**kwargs)

            text_parts: list[str] = []
            # index -> {"id": str, "name": str, "arguments": str}
            tool_call_deltas: dict[int, dict] = {}
            usage = None
            cancelled = False

            for chunk in stream_ctx:
                if should_stop and should_stop():
                    cancelled = True
                    break
                if getattr(chunk, "usage", None):
                    usage = chunk.usage
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    text_parts.append(delta.content)
                    if on_delta:
                        on_delta(delta.content)
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        acc = tool_call_deltas.setdefault(
                            tc_delta.index, {"id": None, "name": "", "arguments": ""}
                        )
                        if tc_delta.id:
                            acc["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                acc["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                acc["arguments"] += tc_delta.function.arguments
        except Exception as e:
            raise self._normalize_error(e) from e
        finally:
            close = getattr(stream_ctx, "close", None)
            if callable(close):
                close()

        if cancelled:
            raise InterruptedError("cancelled mid-stream")

        duration_ms = int((time.time() - start) * 1000)
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        tool_calls = None
        if tool_call_deltas:
            tool_calls = [
                ToolCall(id=v["id"], function={"name": v["name"], "arguments": v["arguments"]})
                for _, v in sorted(tool_call_deltas.items())
            ]

        return LLMResult(
            text="".join(text_parts),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider="openai",
            tool_calls=tool_calls,
        )

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
