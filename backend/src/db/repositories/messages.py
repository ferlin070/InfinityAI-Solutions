from typing import Optional
from src.db.client import get_supabase


class MessageRepo:
    def __init__(self):
        self._db = get_supabase()

    def create(self, org_id: str, conversation_id: Optional[str], direction: str, sender: str,
               body: Optional[str] = None, media_url: Optional[str] = None,
               external_id: Optional[str] = None, channel_id: Optional[str] = None) -> dict:
        if not channel_id and conversation_id:
            conv = (
                self._db.table("conversations")
                .select("channel_id")
                .eq("id", conversation_id)
                .maybe_single()
                .execute()
            )
            if conv.data:
                channel_id = conv.data["channel_id"]

        data = {
            "org_id": org_id,
            "conversation_id": conversation_id or None,
            "direction": direction,
            "sender": sender,
            "body": body,
            "media_url": media_url,
            "external_id": external_id,
        }
        if channel_id:
            data["channel_id"] = channel_id

        result = (
            self._db.table("messages")
            .upsert(data, on_conflict="channel_id,external_id")
            .execute()
        )
        return result.data[0]

    def get_by_external_id(self, channel_id: str, external_id: str) -> Optional[dict]:
        result = (
            self._db.table("messages")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("external_id", external_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def list_by_conversation(self, org_id: str, conversation_id: str, limit: int = 20) -> list[dict]:
        result = (
            self._db.table("messages")
            .select("*")
            .eq("org_id", org_id)
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(reversed(result.data))
