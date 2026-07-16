import secrets

# In-memory active sessions storage
ACTIVE_SESSIONS = set()

def create_session() -> str:
    """Generate a new secure session token and store it."""
    session_token = secrets.token_hex(16)
    ACTIVE_SESSIONS.add(session_token)
    return session_token

def verify_session(session_token: str | None) -> bool:
    """Check if the session token is active."""
    if not session_token:
        return False
    return session_token in ACTIVE_SESSIONS

def destroy_session(session_token: str | None) -> None:
    """Remove session token if it exists."""
    if session_token and session_token in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(session_token)
