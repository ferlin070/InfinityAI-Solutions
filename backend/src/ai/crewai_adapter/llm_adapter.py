from typing import Any, Callable

from crewai.llms.base_llm import BaseLLM

from src.ai.providers.base import LLMProvider, LLMResult, Message

# CrewAI calls llm.call(...) with either a raw string or a list of role/content dicts.
ResultCallback = Callable[[str, str | None, LLMResult], None]


class InfinityLLMAdapter(BaseLLM):
    """The only bridge between CrewAI and our AI Provider Interface.

    Every `crewai.Agent` in this system is constructed with `llm=InfinityLLMAdapter(...)`.
    CrewAI never sees an OpenAI (or any future provider) SDK directly — see
    docs/architecture/ai-execution-crewai.md §1.2/§5.1.

    MVP does not support CrewAI tool/function-calling (see `tools/` — empty until
    real product/pricing lookups are needed). `supports_function_calling` returning
    False makes CrewAI fall back to plain-text `.call()` + JSON parsing wherever it
    would otherwise use instructor-based structured extraction, which matches the
    existing JSON-assignment parsing already used by `services/logging.extract_json`.
    """

    def __init__(
        self,
        provider: LLMProvider,
        model: str,
        agent_key: str,
        org_id: str | None = None,
        temperature: float | None = 0.7,
        max_tokens: int = 4096,
        on_result: ResultCallback | None = None,
    ) -> None:
        super().__init__(model=model, temperature=temperature)
        self._provider = provider
        self._agent_key = agent_key
        self._org_id = org_id
        self._max_tokens = max_tokens
        self._on_result = on_result

    def call(
        self,
        messages: str | list[dict[str, str]],
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
    ) -> str:
        if tools:
            raise NotImplementedError(
                f"InfinityLLMAdapter for agent '{self._agent_key}' received tool "
                "definitions, but CrewAI tool/function-calling isn't wired up in MVP "
                "(see docs/architecture/ai-execution-crewai.md §2 ai/tools/). "
                "Attach tools only once ai/tools/ has real implementations."
            )

        normalized: list[Message] = (
            [{"role": "user", "content": messages}]
            if isinstance(messages, str)
            else messages
        )

        result = self._provider.complete(
            messages=normalized,
            model=self.model,
            temperature=self.temperature if self.temperature is not None else 0.7,
            max_tokens=self._max_tokens,
        )

        if self._on_result:
            self._on_result(self._agent_key, self._org_id, result)

        return result["text"]

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return _CONTEXT_WINDOWS.get(self.model, 128_000)


# Conservative context-window sizes for cost/guard estimation only — not enforced
# by the provider layer itself (OpenAI's API rejects over-length requests on its own).
_CONTEXT_WINDOWS = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
    "o3-mini": 200_000,
}
