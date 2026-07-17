from typing import Optional
from src.db.client import get_supabase


class ChannelRepo:
    def __init__(self):
        self._db = get_supabase()

    def create(self, org_id: str, phone_number: str,
               channel_type: str = "wa_webjs") -> dict:
        result = (
            self._db.table("channels")
            .insert({
                "org_id": org_id,
                "type": channel_type,
                "phone_number": phone_number,
                "status": "pending_qr",
            })
            .execute()
        )
        return result.data[0]

    def list_by_org(self, org_id: str) -> list[dict]:
        result = (
            self._db.table("channels")
            .select("*")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data

    def get_by_id(self, org_id: str, channel_id: str) -> Optional[dict]:
        result = (
            self._db.table("channels")
            .select("*")
            .eq("org_id", org_id)
            .eq("id", channel_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def update_status(self, org_id: str, channel_id: str, status: str) -> dict:
        result = (
            self._db.table("channels")
            .update({"status": status})
            .eq("org_id", org_id)
            .eq("id", channel_id)
            .execute()
        )
        return result.data[0]

    def delete(self, org_id: str, channel_id: str):
        self._db.table("channels").delete().eq("org_id", org_id).eq("id", channel_id).execute()
