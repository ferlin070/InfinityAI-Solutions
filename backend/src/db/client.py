import os
from typing import Any

_SUPABASE_CLIENT: Any = None


def get_supabase() -> Any:
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
