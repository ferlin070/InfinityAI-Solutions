"""Google Gemini provider. Optional dependency — `pip install google-genai>=1.0`.

Implements `LLMProvider` ABC. Uses the modern `google-genai` SDK (unified
`client.models.generate_content` API) which superseded `google-generativeai`.
Native SDK errors are normalised into our `ProviderError` hierarchy.

Tool/function-calling: Gemini uses `tools=[{function_declarations: [...]}]` on
input and `parts` containing `function_call` on output. We translate to/from
the OpenAI-style `tool_calls` shape used by `LLMResult`.
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

# USD per 1K tokens (approximate; Gemini free tier is often 0).
_PRICING_PER_1K_TOKENS = {
    "gemini-2.5-pro": {"in": 0.00125, "out": 0.01},
    "gemini-2.5-flash": {"in": 0.0003, "out": 0.0025},
    "gemini-2.0-flash": {"in": 0.0001, "out": 0.0004},
    "gemini-1.5-pro": {"in": 0.00125, "out": 0.005},
    "gemini-1.5-flash": {"in": 0.000075, "out": 0.0003},
}


class GeminiProvider(LLMProvider):
    """Google Gemini provider. Wraps `google-genai` — nothing outside this module
    imports the SDK directly."""

    def __init__(self, api_key: str, timeout: float = 60.0):
        try:
            from google import genai
        except ImportError as e:
            raise ProviderError(
                "The 'google-genai' package is not installed. "
                "Add `google-genai>=1.0` to requirements.txt or `pip install google-genai`."
            ) from e
        if not api_key:
            raise ProviderError("Gemini provider requires a non-empty API key.")
        self._genai = genai
        self._client = genai.Client(api_key=api_key)

    def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        start = time.time()
        system_prompt, contents = _to_contents(messages)
        config = {"temperature": temperature, "max_output_tokens": max_tokens}
        if system_prompt:
            config["system_instruction"] = system_prompt
        gemini_tools = None
        if tools:
            gemini_tools = [_to_gemini_tools(tools)]

        try:
            resp = self._client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
                tools=gemini_tools,
            )
        except Exception as e:
            raise self._normalize_error(e) from e

        duration_ms = int((time.time() - start) * 1000)
        text, tool_calls = _flatten_parts(resp)
        meta = getattr(resp, "usage_metadata", None)
        tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0) if meta else 0
        tokens_out = int(getattr(meta, "candidates_token_count", 0) or 0) if meta else 0

        return LLMResult(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=self._estimate_cost(model, tokens_in, tokens_out),
            duration_ms=duration_ms,
            model=model,
            provider="gemini",
            tool_calls=tool_calls,
        )

    def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        system_prompt, contents = _to_contents(messages)
        config = {"temperature": temperature, "max_output_tokens": max_tokens}
        if system_prompt:
            config["system_instruction"] = system_prompt
        try:
            for chunk in self._client.models.generate_content_stream(
                model=model, contents=contents, config=config
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise self._normalize_error(e) from e

    @staticmethod
    def _normalize_error(e: Exception) -> ProviderError:
        msg = str(e).lower()
        cls = type(e).__name__
        if "api key" in msg or "permission" in msg or "unauthenticated" in msg:
            return ProviderAuthError(str(e))
        if "rate" in msg or "quota" in msg or "resource_exhausted" in msg:
            return ProviderRateLimitError(str(e))
        if "deadline" in msg or "timeout" in msg:
            return ProviderTimeoutError(str(e))
        if "context length" in msg or "too long" in msg or "token limit" in msg:
            return ProviderContextLengthError(str(e))
        if cls in ("ClientError",):
            return ProviderError(str(e))
        return ProviderError(str(e))

    @staticmethod
    def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
        rates = _PRICING_PER_1K_TOKENS.get(model)
        if rates is None:
            logger.warning(f"No pricing entry for Gemini model '{model}' — cost_usd recorded as 0.0")
            return 0.0
        return round((tokens_in / 1000) * rates["in"] + (tokens_out / 1000) * rates["out"], 6)


def _to_contents(messages: list[Message]) -> tuple[str, list[dict]]:
    """Translate OpenAI-style `Message` list into Gemini's
    (system_instruction, contents=[{role, parts}]) shape."""
    system_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content") or ""
        if role == "system":
            if content:
                system_parts.append(content)
            continue
        if role == "tool":
            try:
                import json as _json
                payload = _json.loads(content) if isinstance(content, str) else content
            except Exception:
                payload = {"result": content}
            contents.append({
                "role": "user",
                "parts": [{"function_response": {"name": "tool", "response": payload}}],
            })
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return "\n\n".join(system_parts), contents


def _to_gemini_tools(tools: list[dict]) -> dict:
    """Convert a list of OpenAI-style tool defs to a single Gemini
    `{"function_declarations": [...]}` block."""
    declarations = []
    for t in tools:
        fn = t.get("function", {})
        declarations.append({
            "name": fn.get("name", "tool"),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return {"function_declarations": declarations}


def _flatten_parts(resp) -> tuple[str, list[ToolCall] | None]:
    """Walk `resp.candidates[0].content.parts`, collect text and any
    `function_call` parts as normalised `ToolCall` entries."""
    import json as _json

    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    candidates = getattr(resp, "candidates", None) or []
    if not candidates:
        return "", None
    parts = getattr(candidates[0].content, "parts", None) or []
    for idx, part in enumerate(parts):
        if getattr(part, "text", None):
            text_parts.append(part.text)
        fc = getattr(part, "function_call", None)
        if fc is not None:
            tool_calls.append(
                ToolCall(
                    id=f"gemini-fc-{idx}",
                    function={
                        "name": getattr(fc, "name", "tool"),
                        "arguments": _json.dumps(getattr(fc, "args", {}) or {}),
                    },
                )
            )
    return "".join(text_parts), (tool_calls or None)
