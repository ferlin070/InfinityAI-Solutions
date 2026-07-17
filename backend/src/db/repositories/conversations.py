from typing import Optional
from src.db.client import get_supabase


class ConversationRepo:
    def __init__(self):
        self._db = get_supabase()

    def get_open_by_contact(self, org_id: str, contact_id: str) -> Optional[dict]:
        result = (
            self._db.table("conversations")
            .select("*")
            .eq("org_id", org_id)
            .eq("contact_id", contact_id)
            .eq("status", "open")
            .maybe_single()
            .execute()
        )
        return result.data

    def create(self, org_id: str, contact_id: str, channel_id: str) -> dict:
        result = (
            self._db.table("conversations")
            .insert({
                "org_id": org_id,
                "contact_id": contact_id,
                "channel_id": channel_id,
                "status": "open",
                "mode": "ai",
            })
            .execute()
        )
        return result.data[0]

    def set_mode(self, org_id: str, conversation_id: str, mode: str) -> dict:
        result = (
            self._db.table("conversations")
            .update({"mode": mode})
            .eq("org_id", org_id)
            .eq("id", conversation_id)
            .execute()
        )
        return result.data[0]

    def close(self, org_id: str, conversation_id: str) -> dict:
        result = (
            self._db.table("conversations")
            .update({"status": "closed"})
            .eq("org_id", org_id)
            .eq("id", conversation_id)
            .execute()
        )
        return result.data[0]

    def list_open(self, org_id: str) -> list[dict]:
        result = (
            self._db.table("conversations")
            .select("*, contacts(*)")
            .eq("org_id", org_id)
            .eq("status", "open")
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data
