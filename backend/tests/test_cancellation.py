"""Tests for src/ai/agentic/cancellation.py."""

from src.ai.agentic import cancellation


def test_create_cancel_token_is_unique():
    a = cancellation.create_cancel_token()
    b = cancellation.create_cancel_token()
    assert a != b
    cancellation.cleanup(a)
    cancellation.cleanup(b)


def test_is_cancelled_false_before_cancel():
    token = cancellation.create_cancel_token()
    try:
        assert cancellation.is_cancelled(token) is False
    finally:
        cancellation.cleanup(token)


def test_cancel_marks_token_cancelled():
    token = cancellation.create_cancel_token()
    try:
        assert cancellation.cancel(token) is True
        assert cancellation.is_cancelled(token) is True
    finally:
        cancellation.cleanup(token)


def test_cancel_unknown_token_returns_false():
    assert cancellation.cancel("does-not-exist") is False


def test_is_cancelled_unknown_token_is_false_not_an_error():
    assert cancellation.is_cancelled("does-not-exist") is False


def test_cleanup_removes_token():
    token = cancellation.create_cancel_token()
    cancellation.cleanup(token)
    # Once cleaned up, cancel() should report "not found" rather than
    # silently succeeding against a stale entry.
    assert cancellation.cancel(token) is False


def test_cleanup_unknown_token_does_not_raise():
    cancellation.cleanup("does-not-exist")
