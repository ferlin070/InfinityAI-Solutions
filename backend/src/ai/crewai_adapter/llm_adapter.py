import json
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

    Supports tool/function-calling: when `available_functions` are provided and the
    LLM returns `tool_calls`, this adapter executes the functions and re-calls the
    LLM with the results — the tool loop is handled here, not by CrewAI itself.
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
        normalized: list[Message] = (
            [{"role": "user", "content": messages}]
            if isinstance(messages, str)
            else messages
        )

        # Tool loop: call provider, if tool_calls returned, execute functions and repeat
        current_tools = tools
        while True:
            result = self._provider.complete(
                messages=normalized,
                model=self.model,
                temperature=self.temperature if self.temperature is not None else 0.7,
                max_tokens=self._max_tokens,
                tools=current_tools,
            )

            tool_calls = result.get("tool_calls")
            if not tool_calls or not available_functions:
                # No (more) tools to execute — return the text response
                if self._on_result:
                    self._on_result(self._agent_key, self._org_id, result)
                return result["text"]

            # Execute each tool call and append results to messages
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args_raw = tc["function"]["arguments"]
                fn = available_functions.get(fn_name)
                if fn is None:
                    fn_output = f"Error: unknown tool '{fn_name}'"
                else:
                    try:
                        fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                        fn_output = fn(**fn_args) if isinstance(fn_args, dict) else fn(fn_args_raw)
                    except Exception as e:
                        fn_output = f"Error executing {fn_name}: {e}"

                normalized.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": tc["id"], "type": "function", "function": tc["function"]}],
                })
                normalized.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(fn_output),
                })

            # Subsequent iterations don't resend tool definitions
            current_tools = None

    def supports_function_calling(self) -> bool:
        return True

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
