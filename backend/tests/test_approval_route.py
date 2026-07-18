"""Tests for the /api/chat/approval endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.ai.agentic.approval import create_approval, list_pending


def _make_client():
    """Override to inject session — see test_chat_stream_route.py for pattern."""
    from src.api.routes import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def client():
    return _make_client()


class TestApprovalEndpoint:
    def test_unauthenticated(self, client):
        resp = client.post("/api/chat/approval", json={"approval_id": "x", "decision": {}})
        assert resp.status_code == 401

    def test_missing_approval_id(self, client):
        from src.core.sessions import create_session

        token = create_session()
        resp = client.post(
            "/api/chat/approval",
            json={"decision": {"approved": True}},
            cookies={"session_token": token},
        )
        assert resp.status_code == 400

    def test_unknown_approval_id(self, client):
        from src.core.sessions import create_session

        token = create_session()
        resp = client.post(
            "/api/chat/approval",
            json={"approval_id": "nonsense", "decision": {"approved": True}},
            cookies={"session_token": token},
        )
        assert resp.status_code == 404

    def test_approve_success(self, client):
        from src.core.sessions import create_session

        aid = create_approval()
        token = create_session()
        resp = client.post(
            "/api/chat/approval",
            json={"approval_id": aid, "decision": {"approved": True, "reason": "Looks good"}},
            cookies={"session_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["approval_id"] == aid
        assert data["decision"]["approved"] is True

    def test_reject_success(self, client):
        from src.core.sessions import create_session

        aid = create_approval()
        token = create_session()
        resp = client.post(
            "/api/chat/approval",
            json={"approval_id": aid, "decision": {"approved": False, "reason": "Not needed"}},
            cookies={"session_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["decision"]["approved"] is False

    def test_double_approve_returns_ok(self, client):
        """Resolving the same approval twice should work (second call resolves
        the already-set event but returns True because the state still exists
        briefly)."""
        from src.core.sessions import create_session

        aid = create_approval()
        token = create_session()
        resp1 = client.post(
            "/api/chat/approval",
            json={"approval_id": aid, "decision": {"approved": True}},
            cookies={"session_token": token},
        )
        assert resp1.status_code == 200

        # Second call should also succeed since the state is still stored
        resp2 = client.post(
            "/api/chat/approval",
            json={"approval_id": aid, "decision": {"approved": True}},
            cookies={"session_token": token},
        )
        assert resp2.status_code == 200
