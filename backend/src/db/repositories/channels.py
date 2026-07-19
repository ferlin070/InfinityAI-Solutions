from typing import Optional
from src.db.client import get_supabase
from .base import BaseRepo


class ChannelRepo(BaseRepo):
    def __init__(self):
        self._db = get_supabase()

    def create(self, org_id: str, phone_number: str,
               channel_type: str = "wa_webjs") -> dict:
        result = self._exec(
            self._db.table("channels")
            .insert({
                "org_id": org_id,
                "type": channel_type,
                "phone_number": phone_number,
                "status": "pending_qr",
            })
        )
        return result.data[0] if result and result.data else {}

    def list_by_org(self, org_id: str) -> list[dict]:
        result = self._exec(
            self._db.table("channels")
            .select("*")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
        )
        return result.data if result else []

    def get_by_id(self, org_id: str, channel_id: str) -> Optional[dict]:
        result = self._exec(
            self._db.table("channels")
            .select("*")
            .eq("org_id", org_id)
            .eq("id", channel_id)
            .maybe_single()
        )
        return result.data if result else None

    def update_status(self, org_id: str, channel_id: str, status: str) -> dict:
        result = self._exec(
            self._db.table("channels")
            .update({"status": status})
            .eq("org_id", org_id)
            .eq("id", channel_id)
        )
        return result.data[0] if result and result.data else {}

    def delete(self, org_id: str, channel_id: str):
        self._exec(
            self._db.table("channels").delete().eq("org_id", org_id).eq("id", channel_id)
        )
