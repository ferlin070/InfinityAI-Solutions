from abc import ABC, abstractmethod
from typing import Any, Callable, Iterator, TypedDict


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str


class ToolCall(TypedDict):
    id: str
    function: dict  # {"name": str, "arguments": str}


class LLMResult(TypedDict):
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_ms: int
    model: str
    provider: str
    tool_calls: list[ToolCall] | None  # present when LLM requests tool execution


class LLMProvider(ABC):
    """Every concrete provider (OpenAI now, others later) implements this and only this.

    Nothing outside `src/ai/providers/` may import a vendor SDK directly — see
    docs/architecture/ai-execution-crewai.md §4.
    """

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> LLMResult:
        ...

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        ...

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
        """Like `complete()`, but calls `on_delta(chunk)` for each piece of
        assistant text as it becomes available, and checks `should_stop()`
        between/during network I/O to support user-initiated cancellation.

        Default implementation: no real token-level streaming — just calls
        `complete()` once and reports the whole answer as a single delta.
        Providers that can actually stream (OpenAI) should override this.
        Every provider still returns the exact same `LLMResult` shape either
        way, so callers don't need to know which providers stream for real.
        """
        if should_stop and should_stop():
            raise InterruptedError("cancelled before request was sent")
        result = self.complete(messages, model, temperature, max_tokens, tools)
        if on_delta and result["text"]:
            on_delta(result["text"])
        return result
