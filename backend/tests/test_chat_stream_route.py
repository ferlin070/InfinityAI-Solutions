import sys
import os
import json
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.main import app
from src.schemas.models import AgentResult, ExecuteResponse

client = TestClient(app)


def _login() -> str:
    response = client.post(
        "/api/login", json={"email": "bos@infinityai.com", "password": "password123"}
    )
    assert response.status_code == 200
    return response.cookies.get("session_token")


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type, data_line = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data_line = line[len("data: "):]
        if event_type and data_line is not None:
            events.append((event_type, json.loads(data_line)))
    return events


def test_chat_stream_requires_auth():
    response = client.post("/api/chat/stream", json={"prompt": "hai"})
    assert response.status_code == 401


def test_chat_stream_emits_events_then_final_and_persists_turns():
    session_cookie = _login()
    fake_response = ExecuteResponse(status="chat", message="Hai Bos!", model="gpt-4o-mini")

    with patch("src.api.routes.TaskExecutionFlowV2") as MockFlow, \
         patch("src.api.routes.dashboard_memory") as mock_memory:
        mock_memory.get_recent.return_value = []
        instance = MockFlow.return_value

        def _flow_ctor(on_event=None, should_stop=None):
            _flow_ctor.on_event = on_event
            return instance
        MockFlow.side_effect = _flow_ctor

        def _run(**kwargs):
            _flow_ctor.on_event("status", {"text": "Planner sedang menganalisis..."})
            return fake_response
        instance.run.side_effect = _run

        response = client.post(
            "/api/chat/stream",
            json={"prompt": "hai", "model": "gpt-4o-mini"},
            cookies={"session_token": session_cookie},
        )

    assert response.status_code == 200
    events = _parse_sse(response.text)
    event_types = [e[0] for e in events]
    assert "status" in event_types
    assert event_types[-1] == "final"
    assert events[-1][1]["status"] == "chat"
    assert events[-1][1]["message"] == "Hai Bos!"

    mock_memory.append_message.assert_any_call("user", "hai")
    mock_memory.append_message.assert_any_call("assistant", "Hai Bos!")


def test_chat_stream_first_event_is_ready_with_cancel_token():
    session_cookie = _login()
    fake_response = ExecuteResponse(status="chat", message="Hai Bos!", model="gpt-4o-mini")

    with patch("src.api.routes.TaskExecutionFlowV2") as MockFlow, \
         patch("src.api.routes.dashboard_memory") as mock_memory:
        mock_memory.get_recent.return_value = []
        MockFlow.return_value.run.return_value = fake_response

        response = client.post(
            "/api/chat/stream",
            json={"prompt": "hai", "model": "gpt-4o-mini"},
            cookies={"session_token": session_cookie},
        )

    events = _parse_sse(response.text)
    assert events[0][0] == "ready"
    assert "cancel_token" in events[0][1]
    assert events[0][1]["cancel_token"]


def test_chat_cancel_requires_auth():
    # Fresh client — the shared `client` may already carry a session cookie
    # from an earlier test's _login() call (TestClient persists cookies).
    response = TestClient(app).post("/api/chat/cancel", json={"cancel_token": "x"})
    assert response.status_code == 401


def test_chat_cancel_requires_token_field():
    session_cookie = _login()
    response = client.post(
        "/api/chat/cancel", json={}, cookies={"session_token": session_cookie}
    )
    assert response.status_code == 400


def test_chat_cancel_unknown_token_is_not_found_not_an_error():
    session_cookie = _login()
    response = client.post(
        "/api/chat/cancel",
        json={"cancel_token": "does-not-exist"},
        cookies={"session_token": session_cookie},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "not_found"


def test_chat_cancel_known_token_marks_it_cancelled():
    from src.ai.agentic import cancellation

    session_cookie = _login()
    token = cancellation.create_cancel_token()
    try:
        response = client.post(
            "/api/chat/cancel",
            json={"cancel_token": token},
            cookies={"session_token": session_cookie},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert cancellation.is_cancelled(token) is True
    finally:
        cancellation.cleanup(token)


def test_chat_stream_reports_error_event_on_exception():
    session_cookie = _login()

    with patch("src.api.routes.TaskExecutionFlowV2") as MockFlow, \
         patch("src.api.routes.dashboard_memory") as mock_memory:
        mock_memory.get_recent.return_value = []
        MockFlow.return_value.run.side_effect = RuntimeError("boom")

        response = client.post(
            "/api/chat/stream",
            json={"prompt": "hai", "model": "gpt-4o-mini"},
            cookies={"session_token": session_cookie},
        )

    events = _parse_sse(response.text)
    assert events[-1][0] == "error"


def test_chat_stream_times_out_if_background_flow_never_responds():
    """Regression test for the production symptom: the chat spinner hangs
    forever with no error surfaced at all. If run_flow's background thread
    never puts anything on the queue (e.g. it's genuinely stuck on a network
    call), the client must still get a terminal error event instead of an
    unbounded hang."""
    session_cookie = _login()

    with patch("src.api.routes.TaskExecutionFlowV2") as MockFlow, \
         patch("src.api.routes.dashboard_memory") as mock_memory, \
         patch("src.api.routes.CHAT_STREAM_TIMEOUT_S", 0.05):
        mock_memory.get_recent.return_value = []
        MockFlow.return_value.run.side_effect = lambda **kw: __import__("time").sleep(5)

        response = client.post(
            "/api/chat/stream",
            json={"prompt": "hai", "model": "gpt-4o-mini"},
            cookies={"session_token": session_cookie},
        )

    events = _parse_sse(response.text)
    assert events[-1][0] == "error"
    assert "Masa tamat" in events[-1][1]["message"]


def test_chat_history_requires_auth():
    # Fresh client — the shared `client` may already carry a session cookie
    # from an earlier test's _login() call (TestClient persists cookies).
    response = TestClient(app).get("/api/chat/history")
    assert response.status_code == 401


def test_chat_history_returns_recent_transcript():
    session_cookie = _login()
    with patch("src.api.routes.dashboard_memory") as mock_memory:
        mock_memory.get_recent.return_value = [{"role": "user", "content": "hai"}]

        response = client.get("/api/chat/history", cookies={"session_token": session_cookie})

    assert response.status_code == 200
    assert response.json() == [{"role": "user", "content": "hai"}]


def test_chat_clear_requires_auth():
    response = TestClient(app).post("/api/chat/clear")
    assert response.status_code == 401


def test_chat_clear_resets_memory():
    session_cookie = _login()
    with patch("src.api.routes.dashboard_memory") as mock_memory:
        response = client.post("/api/chat/clear", cookies={"session_token": session_cookie})

    assert response.status_code == 200
    mock_memory.clear.assert_called_once()
