from abc import ABC, abstractmethod
from typing import Iterator, TypedDict


class Message(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMResult(TypedDict):
    text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_ms: int
    model: str
    provider: str


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
