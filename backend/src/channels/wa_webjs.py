import os
import requests
from typing import Optional
from .base import WhatsAppProvider, InboundMessage


GATEWAY_BASE = os.getenv("GATEWAY_INTERNAL_URL", "http://gateway-wa:3000")
GATEWAY_SECRET = os.getenv("GATEWAY_SHARED_SECRET", "dev-secret-change-in-production")


class WAWebJSProvider(WhatsAppProvider):
    def _headers(self) -> dict:
        return {
            "X-Gateway-Secret": GATEWAY_SECRET,
            "Content-Type": "application/json",
        }

    def send_text(self, channel_id: str, to: str, body: str) -> None:
        resp = requests.post(
            f"{GATEWAY_BASE}/sessions/{channel_id}/send",
            headers=self._headers(),
            json={"to": to, "body": body},
            timeout=10,
        )
        resp.raise_for_status()

    def send_document(self, channel_id: str, to: str, file_url: str,
                      caption: Optional[str] = None) -> None:
        resp = requests.post(
            f"{GATEWAY_BASE}/sessions/{channel_id}/send",
            headers=self._headers(),
            json={"to": to, "fileUrl": file_url, "caption": caption},
            timeout=60,
        )
        resp.raise_for_status()

    def parse_inbound(self, payload: dict) -> InboundMessage:
        return InboundMessage(
            channel_id=payload["channel_id"],
            from_number=payload["from"],
            body=payload.get("body", ""),
            message_id=payload.get("message_id") or payload.get("id", ""),
            timestamp=payload.get("timestamp", 0),
        )

    # ─── Session management ─────────────────────────────────────

    def start_session(self, channel_id: str) -> dict:
        resp = requests.post(
            f"{GATEWAY_BASE}/sessions/{channel_id}/start",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_qr(self, channel_id: str) -> dict:
        resp = requests.get(
            f"{GATEWAY_BASE}/sessions/{channel_id}/qr",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_session_status(self, channel_id: str) -> str:
        resp = requests.get(
            f"{GATEWAY_BASE}/sessions/{channel_id}/status",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("status", "disconnected")

    def destroy_session(self, channel_id: str) -> None:
        requests.delete(
            f"{GATEWAY_BASE}/sessions/{channel_id}",
            headers=self._headers(),
            timeout=10,
        )
