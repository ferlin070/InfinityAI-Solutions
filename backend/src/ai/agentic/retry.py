"""Retry engine — automatic retry on transient tool failures, with
alt-tool fallback when the primary tool is permanently broken.

The current `InfinityLLMAdapter` returns the tool error string to the
LLM, which may or may not recover. Phase 1 adds a structured layer:

- Transient failures (timeout, rate limit, network): retry the same
  tool with exponential backoff, up to `max_retries`.
- Permanent failures (RuntimeError, tool not found, argument error):
  try an `alt_tool` from the registry (if one is registered for the
  same capability) up to `max_alt_attempts`.
- After all attempts exhausted: escalate to the Coordinator (which
  records the failure in the trace and decides whether to ask the user).

This is a pure function over a `ToolCallResult`; it doesn't touch the
LLM directly. The adapter calls it; the retry policy lives here.
"""

import time
from dataclasses import dataclass
from typing import Optional

from src.ai.crewai_adapter.llm_adapter import EventCallback
from src.core.config import logger


# Error signatures that should trigger a retry (transient).
_TRANSIENT_ERROR_SIGNALS = (
    "timeout",
    "timed out",
    "rate limit",
    "ratelimit",
    "429",
    "500",
    "502",
    "503",
    "504",
    "connection",
    "temporarily",
)


@dataclass
class ToolCallResult:
    """What a tool call produced (or failed to produce)."""
    success: bool
    output: str
    error: Optional[str] = None
    attempts: int = 1
    fell_back_to: Optional[str] = None  # if we used an alt tool


class RetryEngine:
    """Decides whether to retry a failed tool call. Stateless — pass
    the same config every time.

    `alt_tools` is a dict mapping primary tool name to a fallback name
    (or list of names, tried in order). Populate it from the
    ToolRegistry once we have capability metadata (Phase 2)."""

    def __init__(
        self,
        max_retries: int = 2,
        initial_backoff_s: float = 0.5,
        backoff_factor: float = 2.0,
        alt_tools: Optional[dict[str, str | list[str]]] = None,
    ):
        self.max_retries = max_retries
        self.initial_backoff_s = initial_backoff_s
        self.backoff_factor = backoff_factor
        self.alt_tools = alt_tools or {}

    def is_transient(self, error: Optional[str]) -> bool:
        if not error:
            return False
        e = error.lower()
        return any(sig in e for sig in _TRANSIENT_ERROR_SIGNALS)

    def should_retry(self, error: Optional[str], attempt: int) -> bool:
        return self.is_transient(error) and attempt <= self.max_retries

    def alt_tool_for(self, primary: str) -> Optional[str]:
        """Return the next alt tool to try for `primary`, or None if
        no fallback is registered. Caller invokes it; if it also
        fails, they can call this again to get the next one."""
        alts = self.alt_tools.get(primary)
        if not alts:
            return None
        if isinstance(alts, str):
            return alts
        return alts[0] if alts else None

    def sleep_for_retry(self, attempt: int) -> float:
        """How long to sleep before retry attempt N (1-indexed).
        Exponential backoff: 0.5s, 1.0s, 2.0s, 4.0s, ..."""
        return self.initial_backoff_s * (self.backoff_factor ** (attempt - 1))

    def execute_with_retry(
        self,
        tool_name: str,
        call_fn,
        on_event: Optional[EventCallback] = None,
    ) -> ToolCallResult:
        """Run `call_fn(tool_name, **kwargs)` with retry + alt-tool
        fallback. `call_fn` is whatever knows how to actually invoke
        the tool (the adapter's local invoker). It should return
        `(success: bool, output: str, error: Optional[str])`.

        `on_event` receives `("tool_retry", {...})` and
        `("tool_fallback", {...})` events so the UI can show 'retrying
        with alt tool' progress.
        """
        attempt = 1
        current_tool = tool_name
        last_error: Optional[str] = None

        while True:
            try:
                success, output, error = call_fn(current_tool)
            except Exception as e:
                success, output, error = False, "", f"Exception: {e}"

            if success:
                return ToolCallResult(
                    success=True,
                    output=output,
                    attempts=attempt,
                    fell_back_to=current_tool if current_tool != tool_name else None,
                )

            last_error = error
            # Transient: retry same tool with backoff
            if self.should_retry(error, attempt):
                sleep_s = self.sleep_for_retry(attempt)
                if on_event:
                    on_event("tool_retry", {
                        "tool": current_tool,
                        "attempt": attempt,
                        "next_in_s": sleep_s,
                        "error": error,
                    })
                time.sleep(sleep_s)
                attempt += 1
                continue

            # Permanent: try alt tool if available
            alt = self.alt_tool_for(current_tool)
            if alt and alt != current_tool:
                if on_event:
                    on_event("tool_fallback", {
                        "from": current_tool,
                        "to": alt,
                        "error": error,
                    })
                current_tool = alt
                attempt = 1
                continue

            # All options exhausted
            return ToolCallResult(
                success=False,
                output=output,
                error=last_error,
                attempts=attempt,
                fell_back_to=current_tool if current_tool != tool_name else None,
            )
