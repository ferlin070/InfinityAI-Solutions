import sys
import os
import hashlib
import hmac
import time

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.sessions import create_session, verify_session, destroy_session, _get_secret


def test_session_flow():
    # 1. Create a session
    token = create_session()
    assert token is not None
    assert len(token) > 0

    # 2. Verify it is valid
    assert verify_session(token) is True

    # 3. Verify an invalid token is False
    assert verify_session("invalid-token") is False
    assert verify_session("") is False
    assert verify_session(None) is False

    # 4. Destroy it
    destroy_session(token)

    # 5. Verify it is no longer valid
    assert verify_session(token) is False


def test_session_expiration(monkeypatch):
    import src.core.sessions

    token = src.core.sessions.create_session()
    assert src.core.sessions.verify_session(token) is True

    # Fake time shift to 25 hours later
    real_time = time.time
    monkeypatch.setattr(src.core.sessions.time, "time", lambda: real_time() + 25 * 60 * 60)

    assert src.core.sessions.verify_session(token) is False


def test_tokens_are_self_verifying_not_looked_up_in_process_state():
    """Regression test for the real production bug: sessions used to be stored
    in a process-local dict (`ACTIVE_SESSIONS = {}`) that resets to empty on
    every backend restart (redeploy, crash, Railway respawn) — invalidating
    every logged-in user's session immediately, which showed up live as
    "refreshing the page logs me out". A token built independently (matching
    create_session's exact format/secret, simulating verification by a fresh
    process instance that never called create_session itself) must still
    verify successfully — proving verify_session doesn't depend on any
    server-local session store, only the token's own signature + timestamp."""
    issued_at = str(int(time.time()))
    nonce = "deadbeefdeadbeef"
    payload = f"{issued_at}.{nonce}"
    signature = hmac.new(_get_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    independently_built_token = f"{payload}.{signature}"

    assert verify_session(independently_built_token) is True


def test_two_sessions_created_in_the_same_second_do_not_collide():
    """Regression test: create_session used to be a pure function of
    (timestamp, secret) with no per-token randomness, so two logins within the
    same wall-clock second produced the *identical* token — in practice this
    showed up as one login's logout silently invalidating a different login's
    token too, and as flaky test collisions."""
    tokens = {create_session() for _ in range(20)}
    assert len(tokens) == 20


def test_tampered_token_is_rejected():
    token = create_session()
    issued_at, nonce, _signature = token.split(".")
    tampered = f"{issued_at}.{nonce}.deadbeef"

    assert verify_session(tampered) is False


def test_malformed_token_is_rejected():
    assert verify_session("no-dot-in-here") is False
    assert verify_session("only.one-dot") is False
    assert verify_session("..") is False
