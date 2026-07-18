from typing import Optional
from src.db.client import get_supabase
from .base import BaseRepo


class ConversationRepo(BaseRepo):
    def __init__(self):
        self._db = get_supabase()

    def get_open_by_contact(self, org_id: str, contact_id: str) -> Optional[dict]:
        result = self._exec(
            self._db.table("conversations")
            .select("*")
            .eq("org_id", org_id)
            .eq("contact_id", contact_id)
            .eq("status", "open")
            .maybe_single()
        )
        return result.data if result else None

    def create(self, org_id: str, contact_id: str, channel_id: str) -> dict:
        result = self._exec(
            self._db.table("conversations")
            .insert({
                "org_id": org_id,
                "contact_id": contact_id,
                "channel_id": channel_id,
                "status": "open",
                "mode": "ai",
            })
        )
        return result.data[0] if result and result.data else {}

    def set_mode(self, org_id: str, conversation_id: str, mode: str) -> dict:
        result = self._exec(
            self._db.table("conversations")
            .update({"mode": mode})
            .eq("org_id", org_id)
            .eq("id", conversation_id)
        )
        return result.data[0] if result and result.data else {}

    def close(self, org_id: str, conversation_id: str) -> dict:
        result = self._exec(
            self._db.table("conversations")
            .update({"status": "closed"})
            .eq("org_id", org_id)
            .eq("id", conversation_id)
        )
        return result.data[0] if result and result.data else {}

    def list_open(self, org_id: str) -> list[dict]:
        result = self._exec(
            self._db.table("conversations")
            .select("*, contacts(*)")
            .eq("org_id", org_id)
            .eq("status", "open")
            .order("updated_at", desc=True)
        )
        return result.data if result else []
