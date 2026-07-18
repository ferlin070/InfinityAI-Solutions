"""Approval workflow — in-memory gating of destructive operations.

The Coordinator pauses execution when a subtask has `approval_required=True`.
It emits an `approval_required` event with a unique `approval_id`, then
blocks on a `threading.Event`. The user's approve/reject POST to
`/api/chat/approval` resolves the event, unblocking the Coordinator.

Two threads coordinate through a shared in-memory dict:
  - Background (SSE stream) thread: calls `set_pending()` and waits.
  - FastAPI (approval POST) thread: calls `resolve()` to unblock.

`resolve()` sets the decision + the threading.Event. The background thread
wakes up, checks the decision, and either proceeds or skips the subtask.
"""

import threading
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.core.config import logger


APPROVAL_TIMEOUT_S = 180  # how long the background thread waits before timing out


@dataclass
class ApprovalState:
    approval_id: str
    event: threading.Event = field(default_factory=threading.Event)
    decision: Optional[dict] = None
    resolved: bool = False


_pending: dict[str, ApprovalState] = {}
_lock = threading.Lock()


def create_approval() -> str:
    """Generate a unique approval ID and return it. The caller (Coordinator)
    later calls `wait_for_approval()` with this ID."""
    aid = uuid.uuid4().hex[:16]
    with _lock:
        _pending[aid] = ApprovalState(approval_id=aid)
    return aid


def resolve_approval(approval_id: str, decision: dict) -> bool:
    """Resolve a pending approval from the /api/chat/approval endpoint.
    Returns True if the approval was found and resolved."""
    with _lock:
        state = _pending.get(approval_id)
        if state is None:
            return False
        state.decision = decision
        state.resolved = True
        state.event.set()
    logger.info(f"Approval {approval_id} resolved: {decision}")
    return True


def wait_for_approval(approval_id: str) -> Optional[dict]:
    """Block the calling thread until the approval is resolved or the
    timeout expires. Returns the decision dict, or None on timeout."""
    with _lock:
        state = _pending.get(approval_id)
    if state is None:
        return None

    if not state.event.wait(timeout=APPROVAL_TIMEOUT_S):
        logger.warning(f"Approval {approval_id} timed out after {APPROVAL_TIMEOUT_S}s")
        with _lock:
            _pending.pop(approval_id, None)
        return {"approved": False, "reason": "Approval request timed out. The operation was cancelled."}

    with _lock:
        state = _pending.pop(approval_id, None)
    return state.decision if state else None


def get_pending(approval_id: str) -> Optional[ApprovalState]:
    with _lock:
        return _pending.get(approval_id)


def list_pending() -> list[dict]:
    with _lock:
        return [
            {"approval_id": aid, "resolved": s.resolved}
            for aid, s in _pending.items()
        ]


def _clear_all():
    """Reset all pending approvals (used in tests)."""
    with _lock:
        _pending.clear()
