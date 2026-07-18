import os
from typing import Any

_SUPABASE_CLIENT: Any = None


def get_supabase() -> Any:
    """Lazily create the Supabase client. Raises RuntimeError if env vars
    are missing — see `db_health()` for a non-raising check tools should
    use to decide whether to fall back to local files / demo data."""
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _SUPABASE_CLIENT = create_client(url, key)
    return _SUPABASE_CLIENT


def db_health() -> dict:
    """Non-raising DB availability check. Returns a dict the agent and the
    /api/configuration endpoints can use to report status to the user.

    Shape:
        {
            "available": bool,
            "mode": "live" | "demo",
            "url": str | None,    # the configured Supabase URL (if any)
            "reason": str,         # human-readable explanation
            "hint": str,           # what to do if not available
        }

    Tools should call this once at the start of their body and, if
    `available is False`, fall back to local files / env / demo data
    rather than raising. This is the design the user asked for after
    hitting 'the agent looks too strict' when the DB wasn't configured
    — every tool should still produce a useful answer.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if url and key:
        return {
            "available": True,
            "mode": "live",
            "url": url,
            "reason": "Supabase env vars are set",
            "hint": "",
        }
    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "available": False,
        "mode": "demo",
        "url": None,
        "reason": f"Supabase env vars missing: {', '.join(missing)}",
        "hint": (
            "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env to enable "
            "live CRM / leads / quotations / WhatsApp channel data. Tools will "
            "fall back to local log files (daily_log.json) and environment "
            "configuration in the meantime."
        ),
    }
