import sys
import os
from unittest.mock import DEFAULT, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _login() -> str:
    response = client.post(
        "/api/login", json={"email": "bos@infinityai.com", "password": "password123"}
    )
    assert response.status_code == 200
    return response.cookies.get("session_token")


def _patch_repos():
    return patch.multiple(
        "src.api.wa_routes",
        ChannelRepo=DEFAULT,
        ConversationRepo=DEFAULT,
        MessageRepo=DEFAULT,
    )


def test_create_channel_offloads_blocking_gateway_call_off_the_event_loop():
    """Regression test for the production symptom: a slow/unreachable WA
    gateway call blocking the single asyncio event loop, freezing every other
    concurrent request (including unrelated /api/chat/stream SSE responses)
    for as long as that one blocking `requests` call takes. If start_session
    is ever called synchronously again instead of via asyncio.to_thread, this
    fails because the mocked provider's return value never reaches the
    thread-pool-shaped assertion below.
    """
    session_cookie = _login()

    with patch("src.api.wa_routes.WAWebJSProvider") as MockProvider, _patch_repos() as mocks:
        mocks["ChannelRepo"].return_value.create.return_value = {"id": "chan-1", "phone_number": "+60123"}
        provider_instance = MockProvider.return_value

        response = client.post(
            "/api/channels",
            json={"phone_number": "+60123"},
            cookies={"session_token": session_cookie},
        )

    assert response.status_code == 200
    assert response.json()["id"] == "chan-1"
    provider_instance.start_session.assert_called_once_with("chan-1")


def test_get_channel_qr_returns_provider_result():
    session_cookie = _login()

    with patch("src.api.wa_routes.WAWebJSProvider") as MockProvider:
        MockProvider.return_value.get_qr.return_value = {"status": "pending_qr", "qr": "data:image/png;base64,abc"}

        response = client.get("/api/channels/chan-1/qr", cookies={"session_token": session_cookie})

    assert response.status_code == 200
    assert response.json()["status"] == "pending_qr"


def test_get_channel_status_updates_repo_with_gateway_status():
    session_cookie = _login()

    with patch("src.api.wa_routes.WAWebJSProvider") as MockProvider, _patch_repos() as mocks:
        MockProvider.return_value.get_session_status.return_value = "connected"

        response = client.get("/api/channels/chan-1/status", cookies={"session_token": session_cookie})

    assert response.status_code == 200
    assert response.json() == {"channel_id": "chan-1", "status": "connected"}
    mocks["ChannelRepo"].return_value.update_status.assert_called_once_with(
        "00000000-0000-0000-0000-000000000001", "chan-1", "connected"
    )


def test_delete_channel_destroys_gateway_session_and_repo_row():
    session_cookie = _login()

    with patch("src.api.wa_routes.WAWebJSProvider") as MockProvider, _patch_repos() as mocks:
        response = client.delete("/api/channels/chan-1", cookies={"session_token": session_cookie})

    assert response.status_code == 200
    MockProvider.return_value.destroy_session.assert_called_once_with("chan-1")
    mocks["ChannelRepo"].return_value.delete.assert_called_once()


def test_send_message_calls_gateway_send_text():
    session_cookie = _login()

    with patch("src.api.wa_routes.WAWebJSProvider") as MockProvider, _patch_repos() as mocks:
        mocks["ConversationRepo"].return_value.list_open.return_value = [{"id": "conv-1"}]

        response = client.post(
            "/api/conversations/conv-1/send",
            json={"body": "hai", "channel_id": "chan-1", "to": "+60123"},
            cookies={"session_token": session_cookie},
        )

    assert response.status_code == 200
    MockProvider.return_value.send_text.assert_called_once_with("chan-1", "+60123", "hai")
