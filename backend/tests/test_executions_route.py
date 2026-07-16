import sys
import os
from unittest.mock import AsyncMock, patch

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


def test_create_execution_requires_auth():
    response = client.post("/api/executions", json={"prompt": "kira bajet"})
    assert response.status_code == 401


def test_create_execution_returns_flow_result():
    session_cookie = _login()
    fake_response = ExecuteResponse(
        status="success",
        results=[AgentResult(agent="ZARA", task="kira bajet", result="RM5,000", speed="1.20s")],
        total_speed="1.50s",
        model="gpt-4o-mini",
    )

    with patch("src.api.routes.TaskExecutionFlow") as MockFlow:
        MockFlow.return_value.kickoff_async = AsyncMock(return_value=fake_response)

        response = client.post(
            "/api/executions",
            json={"prompt": "kira bajet pemasaran"},
            cookies={"session_token": session_cookie},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["results"][0]["agent"] == "ZARA"

    kickoff_kwargs = MockFlow.return_value.kickoff_async.call_args.kwargs
    assert kickoff_kwargs["inputs"]["prompt"] == "kira bajet pemasaran"
    assert kickoff_kwargs["inputs"]["org_id"] is None


def test_create_execution_defaults_model_to_gpt_4o_mini():
    session_cookie = _login()
    fake_response = ExecuteResponse(status="success", results=[], total_speed="0.10s", model="gpt-4o-mini")

    with patch("src.api.routes.TaskExecutionFlow") as MockFlow:
        MockFlow.return_value.kickoff_async = AsyncMock(return_value=fake_response)

        client.post(
            "/api/executions",
            json={"prompt": "hi"},
            cookies={"session_token": session_cookie},
        )

    kickoff_kwargs = MockFlow.return_value.kickoff_async.call_args.kwargs
    assert kickoff_kwargs["inputs"]["model"] == "gpt-4o-mini"
