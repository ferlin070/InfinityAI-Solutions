from typing import Optional
from src.db.client import get_supabase
from .base import BaseRepo


class ContactRepo(BaseRepo):
    def __init__(self):
        self._db = get_supabase()

    def get_by_phone(self, org_id: str, phone: str) -> Optional[dict]:
        result = self._exec(
            self._db.table("contacts")
            .select("*")
            .eq("org_id", org_id)
            .eq("phone", phone)
            .maybe_single()
        )
        return result.data if result else None

    def upsert(self, org_id: str, phone: str, name: Optional[str] = None, source: str = "whatsapp", tags: Optional[list[str]] = None) -> dict:
        payload = {"org_id": org_id, "phone": phone, "source": source}
        if name is not None:
            payload["name"] = name
        if tags is not None:
            payload["tags"] = tags
        result = self._exec(
            self._db.table("contacts")
            .upsert(payload, on_conflict="org_id,phone")
        )
        return result.data[0] if result and result.data else payload

    def update_tags(self, org_id: str, contact_id: str, tags: list[str]) -> dict:
        result = self._exec(
            self._db.table("contacts")
            .update({"tags": tags})
            .eq("org_id", org_id)
            .eq("id", contact_id)
        )
        return result.data[0] if result and result.data else {}

    def list_by_org(self, org_id: str) -> list[dict]:
        result = self._exec(
            self._db.table("contacts")
            .select("*")
            .eq("org_id", org_id)
            .order("created_at", desc=True)
        )
        return result.data if result else []
