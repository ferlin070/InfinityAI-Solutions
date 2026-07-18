"""Anthropic provider (Claude). Optional dependency — `pip install anthropic>=0.40`.

Implements the same `LLMProvider` ABC as OpenAI so the rest of the system
(agents, flows, adapter) is provider-unaware. Native SDK errors are normalised
into our `ProviderError` hierarchy in `src/ai/providers/errors.py`.

Tool/function-calling: Anthropic uses `tools=[{"name", "description", "input_schema"}]`
on input and `content=[{"type": "tool_use", "id", "name", "input"}]` on output. We
translate to/from the OpenAI-style `tool_calls=[{"id","function":{"name","arguments"}}]`
shape that `LLMResult` already expects, so the existing tool loop in
`InfinityLLMAdapter.call()` keeps working unchanged.
"""

import time
from typing import Iterator

from src.ai.providers.base import LLMProvider, LLMResult, Message, ToolCall
from src.ai.providers.errors import (
    ProviderAuthError,
    ProviderContextLengthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.config import logger

# USD per 1K tokens. Anthropic prices updated 2026-Q1 baseline; missing models
# fall through and log cost_usd=0.0 (same fail-open behaviour as OpenAI provider).
_PRICING_PER_1K_TOKENS = {
    "claude-opus-4-7": {"in": 0.015, "out": 0.075},
    "claude-sonnet-4-5": {"in": 0.003, "out": 0.015},
    "claude-haiku-4-5": {"in": 0.0008, "out": 0.004},
    "claude-3-5-sonnet-latest": {"in": 0.003, "out": 0.015},
    "claude-3-5-haiku-latest": {"in": 0.0008, "out": 0.004},
    "claude-3-opus-latest": {"in": 0.015, "out": 0.075},
}


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider. Wraps the `anthropic` SDK — nothing outside this
    module imports `anthropic` directly (mirrors the OpenAI provider's contract)."""

    def __init__(self, api_key: str, timeout: float = 60.0):
        try:
            import anthropic
        except ImportError as e:
            raise ProviderError(
                "The 'anthropic' package is not installed. "
                "Add `anthropic>=0.40` to requirements.txt or `pip install anthropic`."
            ) from e
        self._client = anthropic.Anthropic(api_key=api_key or "missing_key", timeout=timeout)

    def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        import anthropic

        start = time.time()
        system_prompt, user_messages = _split_system(messages)
        kwargs = dict(
            model=model,
            messages=user_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = [_to_anthropic_tool(t) for t in tools]

        try:
            resp = self._client.messages.create(**kwargs)
        except Exception as e:
            raise self._normalize_error(e) from e

        duration_ms = int((time.time() - start) * 1000)
        text, tool_calls = _flatten_content(resp.content)
        tokens_in = (resp.usage.input_tokens or 0) if resp.usage else 0
        tokens_out = (resp.usage.output_tokens or 0) if resp.usage else 0

        return LLMResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider="anthropic",
            tool_calls=tool_calls,
        )

    def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        import anthropic

        system_prompt, user_messages = _split_system(messages)
        kwargs = dict(
            model=model,
            messages=user_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise self._normalize_error(e) from e

    @staticmethod
    def _normalize_error(e: Exception) -> ProviderError:
        import anthropic

        if isinstance(e, anthropic.AuthenticationError):
            return ProviderAuthError(str(e))
        if isinstance(e, anthropic.RateLimitError):
            return ProviderRateLimitError(str(e))
        if isinstance(e, anthropic.APITimeoutError):
            return ProviderTimeoutError(str(e))
        if isinstance(e, anthropic.BadRequestError) and "prompt is too long" in str(e).lower():
            return ProviderContextLengthError(str(e))
        return ProviderError(str(e))

    @staticmethod
    def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
        rates = _PRICING_PER_1K_TOKENS.get(model)
        if rates is None:
            logger.warning(f"No pricing entry for Anthropic model '{model}' — cost_usd recorded as 0.0")
            return 0.0
        return round((tokens_in / 1000) * rates["in"] + (tokens_out / 1000) * rates["out"], 6)


def _split_system(messages: list[Message]) -> tuple[str, list[Message]]:
    """Anthropic takes the system prompt as a top-level field, not as a message.
    Pull it out and return (system_text, messages_without_system)."""
    system_parts: list[str] = []
    remaining: list[Message] = []
    for m in messages:
        if m.get("role") == "system":
            content = m.get("content") or ""
            if content:
                system_parts.append(content)
        else:
            remaining.append(m)
    return "\n\n".join(system_parts), remaining


def _to_anthropic_tool(tool: dict) -> dict:
    """Convert OpenAI-style tool def `{type:'function', function:{name,description,parameters}}`
    to Anthropic's `{name, description, input_schema}` shape."""
    fn = tool.get("function", {})
    return {
        "name": fn.get("name", "tool"),
        "description": fn.get("description", ""),
        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
    }


def _flatten_content(content_blocks: list) -> tuple[str, list[ToolCall] | None]:
    """Anthropic returns a list of typed blocks. Pull text into one string and
    `tool_use` blocks into our normalised `ToolCall` list."""
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in content_blocks:
        btype = getattr(block, "type", None)
        if btype == "text":
            text_parts.append(getattr(block, "text", "") or "")
        elif btype == "tool_use":
            import json as _json
            tool_calls.append(
                ToolCall(
                    id=block.id,
                    function={
                        "name": block.name,
                        "arguments": _json.dumps(block.input or {}),
                    },
                )
            )
    text = "".join(text_parts)
    return text, (tool_calls or None)
