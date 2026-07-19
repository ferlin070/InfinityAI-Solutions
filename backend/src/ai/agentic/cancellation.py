"""Cancellation — lets a user Stop a run that's already in flight.

Mirrors `approval.py`'s shape (module-level dict + lock) but is much
simpler: no blocking/waiting, just a flag. `chat_stream` (routes.py)
creates a token per SSE stream and hands `is_cancelled(token)` down
through TaskExecutionFlowV2 -> Coordinator -> Worker -> InfinityLLMAdapter
-> the provider's `stream_complete(should_stop=...)`, which checks it
between chunks so a Stop click can interrupt mid-token-stream, not just
between whole subtasks.

Same in-memory-only tradeoff as approval.py: a token doesn't survive a
backend restart. That's fine here — a cancel token only needs to live for
the seconds-to-minutes of one in-flight stream, never persisted or relied
on across a restart.
"""

import threading
import uuid


class ExecutionCancelled(Exception):
    """Raised when a subtask/dispatch loop notices should_stop() is true.
    Distinct from InterruptedError (which the provider/adapter layers raise
    for the same reason) so callers can tell "I checked and stopped myself"
    apart from "the LLM call itself got interrupted mid-flight" if that
    distinction ever matters — today both are handled the same way."""


_cancelled: dict[str, threading.Event] = {}
_lock = threading.Lock()


def create_cancel_token() -> str:
    token = uuid.uuid4().hex[:16]
    with _lock:
        _cancelled[token] = threading.Event()
    return token


def cancel(token: str) -> bool:
    """Mark `token` as cancelled. Returns False if the token is unknown
    (already cleaned up, or never existed) — the caller should treat that
    as "nothing to cancel", not an error; the run may have already
    finished naturally before the Stop click landed."""
    with _lock:
        event = _cancelled.get(token)
    if event is None:
        return False
    event.set()
    return True


def is_cancelled(token: str) -> bool:
    with _lock:
        event = _cancelled.get(token)
    return event.is_set() if event else False


def cleanup(token: str) -> None:
    """Drop the token once its stream has ended (success, error, or
    cancellation) — otherwise this dict grows for the life of the process."""
    with _lock:
        _cancelled.pop(token, None)
