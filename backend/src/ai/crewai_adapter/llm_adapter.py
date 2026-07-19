import json
import re
from typing import Any, Callable

from crewai.llms.base_llm import BaseLLM

from src.ai.providers.base import LLMProvider, LLMResult, Message

# CrewAI calls llm.call(...) with either a raw string or a list of role/content dicts.
ResultCallback = Callable[[str, str | None, LLMResult], None]
# Fired around tool-call execution for live progress reporting (event_type, payload).
EventCallback = Callable[[str, dict], None]


def _make_tool_caller(agent_tool: Any) -> Callable[..., Any]:
    """Bind `agent_tool` by value (not by loop variable reference) so each tool
    built in `InfinityLLMAdapter._build_tool_schema`'s loop calls the right one."""
    def _call(**kwargs: Any) -> Any:
        return agent_tool.run(**kwargs)
    return _call


class InfinityLLMAdapter(BaseLLM):
    """The only bridge between CrewAI and our AI Provider Interface.

    Every `crewai.Agent` in this system is constructed with `llm=InfinityLLMAdapter(...)`.
    CrewAI never sees an OpenAI (or any future provider) SDK directly — see
    docs/architecture/ai-execution-crewai.md §1.2/§5.1.

    Supports tool/function-calling: when `available_functions` are provided and the
    LLM returns `tool_calls`, this adapter executes the functions and re-calls the
    LLM with the results — the tool loop is handled here, not by CrewAI itself.

    CrewAI's own `CrewAgentExecutor` (crewai/agents/crew_agent_executor.py,
    `get_llm_response`) never actually passes `tools`/`available_functions` to a
    custom `BaseLLM.call()` (nor `from_agent` — only `from_task`) — it drives tool
    use through its own ReAct-style text parsing instead (`Action: ...\\nAction
    Input: ...`), which this adapter's OpenAI-native provider doesn't speak. So
    when neither is supplied, `call()` builds them itself from the assigned
    Task/Agent's `.tools` and resolves the whole tool loop internally — CrewAI's
    executor only ever sees the final plain-text answer, which its fallback
    parser already accepts as a valid `AgentFinish`.
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
        on_event: EventCallback | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(model=model, temperature=temperature)
        self._provider = provider
        self._agent_key = agent_key
        self._org_id = org_id
        self._max_tokens = max_tokens
        self._on_result = on_result
        self._on_event = on_event or (lambda event_type, payload: None)
        # Checked before/during each LLM round-trip so a user-initiated Stop
        # can interrupt a run between tool calls, and even mid-token-stream
        # (see OpenAIProvider.stream_complete) — not just before the whole
        # subtask starts. Cancellation raises InterruptedError, which the
        # Worker (one level up) catches and turns into a "cancelled" result.
        self._should_stop = should_stop

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

        if tools is None and available_functions is None:
            # CrewAgentExecutor._invoke_loop only ever forwards `from_task` (never
            # `from_agent`, despite call()'s signature accepting it) — Task carries
            # its own `.tools` (falling back to `task.agent.tools` internally, see
            # crewai/task.py), so that's the reliable source, with a direct
            # `from_agent.tools` read kept as a fallback for any other call site.
            agent_tools = None
            if from_task is not None:
                agent_tools = getattr(from_task, "tools", None) or getattr(
                    getattr(from_task, "agent", None), "tools", None
                )
            if not agent_tools and from_agent is not None:
                agent_tools = getattr(from_agent, "tools", None)
            if agent_tools:
                tools, available_functions = self._build_tool_schema(agent_tools)

        def _emit_delta(chunk: str) -> None:
            # PLANNER calls only ever produce routing JSON, never user-facing
            # prose — streaming its raw partial JSON into the chat timeline
            # would just be noise, so it's the one agent_key excluded here.
            if self._agent_key != "PLANNER":
                self._on_event("token", {"agent": self._agent_key, "delta": chunk})

        # Tool loop: call provider, if tool_calls returned, execute functions and repeat
        current_tools = tools
        while True:
            if self._should_stop and self._should_stop():
                raise InterruptedError(f"cancelled before LLM call for '{self._agent_key}'")
            result = self._provider.stream_complete(
                messages=normalized,
                model=self.model,
                temperature=self.temperature if self.temperature is not None else 0.7,
                max_tokens=self._max_tokens,
                tools=current_tools,
                on_delta=_emit_delta,
                should_stop=self._should_stop,
            )

            tool_calls = result.get("tool_calls")
            if not tool_calls or not available_functions:
                # No (more) tools to execute — return the text response
                if self._on_result:
                    self._on_result(self._agent_key, self._org_id, result)
                return result["text"]

            # Execute each tool call, then append a SINGLE assistant message
            # containing all the tool_calls plus one tool result per call.
            # (One assistant turn = one message, even with multiple parallel
            # calls. This matches OpenAI/Anthropic/Gemini conventions; the
            # previous per-call assistant message shape was rejected by
            # providers that expect a single message per turn.)
            executed_results: list[dict] = []
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args_raw = tc["function"]["arguments"]
                fn = available_functions.get(fn_name)
                if fn is None:
                    fn_output = f"Error: unknown tool '{fn_name}'"
                    executed_results.append({"id": tc["id"], "output": fn_output})
                    continue

                self._on_event("tool_call", {
                    "agent": self._agent_key, "tool": fn_name, "status": "start"
                })
                try:
                    fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                    fn_output = fn(**fn_args) if isinstance(fn_args, dict) else fn(fn_args_raw)
                except Exception as e:
                    fn_output = f"Error executing {fn_name}: {e}"
                finally:
                    self._on_event("tool_call", {
                        "agent": self._agent_key, "tool": fn_name, "status": "done"
                    })
                # Emit an `observation` event with the actual tool result
                # so the Agent Workspace UI can render a full
                # ToolExecutionCard (args + result). Truncated to 4 KB
                # to keep the SSE stream light.
                obs = str(fn_output)
                if len(obs) > 4000:
                    obs = obs[:4000] + "... [truncated]"
                self._on_event("observation", {
                    "agent": self._agent_key,
                    "tool": fn_name,
                    "arguments": fn_args if isinstance(fn_args, dict) else {},
                    "result": obs,
                    "success": not str(fn_output).lower().startswith("error"),
                })
                executed_results.append({"id": tc["id"], "output": str(fn_output)})

            normalized.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function", "function": tc["function"]}
                    for tc in tool_calls
                ],
            })
            for er in executed_results:
                normalized.append({
                    "role": "tool",
                    "tool_call_id": er["id"],
                    "content": er["output"],
                })

            # Subsequent iterations don't resend tool definitions
            current_tools = None

    @staticmethod
    def _build_tool_schema(agent_tools: list[Any]) -> tuple[list[dict], dict[str, Callable]]:
        """Turn a crewai Agent's `.tools` (crewai.tools.base_tool.Tool instances) into
        an OpenAI-style `tools` schema plus a name -> callable map, so this adapter's
        own tool loop (see `call()`) can run them the same way it would if CrewAI had
        passed them in directly."""
        tools_schema: list[dict] = []
        available_functions: dict[str, Callable] = {}

        for agent_tool in agent_tools:
            # OpenAI function names must match ^[a-zA-Z0-9_-]+$ — tool display
            # names like "Image Generation" or "Contact Info" contain spaces.
            fn_name = re.sub(r"[^a-zA-Z0-9_-]", "_", agent_tool.name)
            args_schema = getattr(agent_tool, "args_schema", None)
            parameters = (
                args_schema.model_json_schema()
                if args_schema is not None
                else {"type": "object", "properties": {}}
            )
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": agent_tool.description or "",
                    "parameters": parameters,
                },
            })
            available_functions[fn_name] = _make_tool_caller(agent_tool)

        return tools_schema, available_functions

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
