from typing import Optional
from src.db.client import get_supabase


class LeadRepo:
    def __init__(self):
        self._db = get_supabase()

    def get_by_contact(self, org_id: str, contact_id: str) -> Optional[dict]:
        result = (
            self._db.table("leads")
            .select("*")
            .eq("org_id", org_id)
            .eq("contact_id", contact_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def upsert(self, org_id: str, contact_id: str, score: str = "cold",
               status: str = "new", interest_summary: Optional[str] = None,
               score_reason: Optional[str] = None) -> dict:
        payload = {
            "org_id": org_id,
            "contact_id": contact_id,
            "score": score,
            "status": status,
            "interest_summary": interest_summary,
            "score_reason": score_reason,
        }
        result = (
            self._db.table("leads")
            .upsert(payload, on_conflict="contact_id")
            .execute()
        )
        return result.data[0]

    def list_by_org(self, org_id: str, score_filter: Optional[str] = None) -> list[dict]:
        query = (
            self._db.table("leads")
            .select("*, contacts(*)")
            .eq("org_id", org_id)
        )
        if score_filter:
            query = query.eq("score", score_filter)
        result = query.order("updated_at", desc=True).execute()
        return result.data
