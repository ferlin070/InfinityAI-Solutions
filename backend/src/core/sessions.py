import hashlib
import hmac
import os
import secrets
import time

_TOKEN_TTL_SECONDS = 24 * 60 * 60

# Best-effort explicit-logout revocation only — in-memory, so it does NOT
# survive a process restart. That's an accepted, minor tradeoff (a token
# explicitly logged out right before a restart becomes valid again until its
# natural 24h expiry) — NOT the bug this module fixes. The actual production
# bug was every *valid, unexpired* session being wiped by a mere backend
# restart (redeploy, crash, Railway respawn), forcing every open tab back to
# login — because the old design stored sessions in a process-local dict
# (`ACTIVE_SESSIONS = {}`) that resets to empty every time the process starts.
# Tokens are now self-verifying (HMAC-signed against SESSION_SECRET_KEY) so a
# restart alone no longer invalidates anything.
_REVOKED_TOKENS: set[str] = set()


def _get_secret() -> str:
    secret = os.getenv("SESSION_SECRET_KEY")
    if secret:
        return secret
    # Dev-only fallback so local runs / tests don't need extra setup — derived
    # from ADMIN_PASSWORD so it's at least per-deployment, not a shared
    # constant. core/config.py's verify_environment() warns loudly if this
    # path is ever hit in production.
    fallback_seed = os.getenv("ADMIN_PASSWORD") or "insecure-dev-only-session-secret"
    return hashlib.sha256(fallback_seed.encode()).hexdigest()


def create_session() -> str:
    """Issue a stateless, HMAC-signed session token:
    `<issued_at>.<nonce>.<signature>`. Self-verifying (see verify_session) —
    no server-side lookup table. The random nonce isn't just extra entropy —
    without it, two logins in the same wall-clock second would produce the
    *identical* token (pure function of timestamp + secret), which is both a
    forgeability weakness and, concretely, made automated tests flake/collide
    whenever two logins landed in the same second."""
    issued_at = str(int(time.time()))
    nonce = secrets.token_hex(8)
    payload = f"{issued_at}.{nonce}"
    signature = hmac.new(_get_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session(session_token: str | None) -> bool:
    """Check if the session token is authentic and not expired (24 hours)."""
    if not session_token or session_token.count(".") != 2:
        return False
    if session_token in _REVOKED_TOKENS:
        return False

    issued_at_str, nonce, signature = session_token.split(".")
    payload = f"{issued_at_str}.{nonce}"
    expected_signature = hmac.new(_get_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return False

    try:
        issued_at = int(issued_at_str)
    except ValueError:
        return False

    return (time.time() - issued_at) <= _TOKEN_TTL_SECONDS


def destroy_session(session_token: str | None) -> None:
    """Revoke a token immediately (explicit logout) — see _REVOKED_TOKENS docstring."""
    if session_token:
        _REVOKED_TOKENS.add(session_token)
