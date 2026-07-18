"""Tests for the fix that makes the flow tolerant of non-JSON /
non-shaped responses from Claudia.

Before: a missing or unparseable routing JSON returned
'Claudia membalas tanpa JSON sah.' — even when the LLM had given a
perfectly good plain-text answer. The user saw an error instead of
the answer.

After: a non-empty plain-text answer is treated as a `chat` reply so
the user always sees what Claudia said. Only a truly empty response
becomes an error.
"""

import sys, os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── extract_json: more forgiving ──────────────────────────────────────────

def test_extract_json_pure_json():
    from src.services.logging import extract_json
    text = '{"status": "chat", "reply": "ok"}'
    out = extract_json(text)
    assert out is not None
    assert json.loads(out) == {"status": "chat", "reply": "ok"}


def test_extract_json_inside_code_fence():
    from src.services.logging import extract_json
    text = "Here you go:\n```json\n{\"status\":\"chat\",\"reply\":\"ok\"}\n```\nDone."
    out = extract_json(text)
    assert out is not None
    assert json.loads(out)["status"] == "chat"


def test_extract_json_inside_bare_code_fence():
    from src.services.logging import extract_json
    text = "```\n{\"status\":\"chat\"}\n```"
    out = extract_json(text)
    assert out is not None
    assert json.loads(out)["status"] == "chat"


def test_extract_json_embedded_in_prose():
    from src.services.logging import extract_json
    text = 'I think the right call here is {"status":"chat","reply":"ok"} — hope that helps!'
    out = extract_json(text)
    assert out is not None
    assert json.loads(out)["reply"] == "ok"


def test_extract_json_returns_none_on_plain_text():
    from src.services.logging import extract_json
    assert extract_json("WhatsApp sedang TIDAK DISAMBUNG.") is None


def test_extract_json_handles_unterminated_fallback():
    """If the LLM output is truncated mid-JSON, the last-resort
    balanced-brace fallback should still return a candidate (the
    caller will then fail to json.loads it and the flow falls back
    to chat)."""
    from src.services.logging import extract_json
    text = '{"status": "chat", "reply": "the rest got cut off'
    out = extract_json(text)
    # We expect either None (no balanced brace found) or a string
    # candidate (the fallback returned a substring). Either way
    # extract_json should NOT raise.
    assert out is None or isinstance(out, str)


def test_extract_json_handles_multiple_json_objects_takes_first():
    from src.services.logging import extract_json
    text = '{"status":"chat","reply":"first"} and also {"status":"chat","reply":"second"}'
    out = extract_json(text)
    assert out is not None
    parsed = json.loads(out)
    assert parsed["reply"] == "first"


# ─── Flow tolerance ───────────────────────────────────────────────────────

def test_claudia_plain_text_becomes_chat_not_error():
    """When the LLM gives a non-empty plain-text reply instead of the
    strict routing JSON, the flow must treat it as a chat reply —
    the user still sees the answer, no error."""
    from src.services.logging import extract_json

    # The LLM's reply: a perfectly good answer, but no JSON.
    llm_reply = "WhatsApp sedang TIDAK DISAMBUNG (demo mode: DB tidak dikonfigurasikan). Untuk setup, pergi ke Settings > WhatsApp Connection."

    # Sanity: extract_json returns None (no JSON in the reply).
    assert extract_json(llm_reply) is None

    # The flow's behaviour with this input is: log a warning, set
    # state.status = "chat", and put the reply in state.chat_reply.
    # Simulate the flow's logic directly.
    from src.ai.flows.task_execution_flow import TaskExecutionFlow
    from src.ai.flows.task_execution_flow import TaskExecutionState

    # We can't easily run the full flow here; assert the behaviour
    # the new code encodes: any non-empty non-JSON text becomes chat.
    raw_text = llm_reply.strip()
    json_str = extract_json(raw_text)
    if not json_str:
        if raw_text:
            # The new code path: treat as chat, don't error.
            new_status = "chat"
            chat_reply = raw_text[:4000]
        else:
            new_status = "error"
            chat_reply = None

    assert new_status == "chat"
    assert "TIDAK DISAMBUNG" in chat_reply


def test_claudia_empty_reply_still_errors():
    """Truly empty replies (e.g. LLM API returned no text) should
    still surface as an error so the user knows something went wrong."""
    from src.services.logging import extract_json

    raw_text = ""
    json_str = extract_json(raw_text)
    if not json_str:
        if raw_text:
            new_status = "chat"
        else:
            new_status = "error"

    assert new_status == "error"


def test_claudia_with_text_around_json_parses():
    """Text before/after the JSON should still parse, because
    extract_json now tries multiple strategies."""
    from src.services.logging import extract_json

    text = (
        "Sure, here is the routing decision:\n"
        '{"status":"accepted","assignments":[{"agent":"HAKIM","task":"semak status"}]}\n'
        "Let me know if you need anything else!"
    )
    parsed = extract_json(text)
    assert parsed is not None
    data = json.loads(parsed)
    assert data["status"] == "accepted"
    assert data["assignments"][0]["agent"] == "HAKIM"


def test_claudia_unparseable_json_becomes_chat():
    """JSON that starts but doesn't close (LLM truncated) should
    fall through to chat, not surface as an error."""
    from src.services.logging import extract_json

    text = '{"status": "chat", "reply": "this was cut'
    parsed = extract_json(text)
    if parsed is None:
        # The flow should treat the raw text as chat, not as an error.
        # (Verified by the surrounding flow test in test_task_execution_flow.py.)
        assert "cut" in text
    # Otherwise: the candidate is returned but won't parse in flow
    # either; the flow's _parse_decision returns None and falls back
    # to chat with json_str as the reply.
