from datetime import date
from typing import Optional
from src.db.client import get_supabase


class ReportRepo:
    def __init__(self):
        self._db = get_supabase()

    def create(self, org_id: str, report_type: str, period_start: date,
               period_end: date, content_md: str,
               delivered_via: Optional[str] = None) -> dict:
        result = (
            self._db.table("reports")
            .insert({
                "org_id": org_id,
                "type": report_type,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "content_md": content_md,
                "delivered_via": delivered_via,
            })
            .execute()
        )
        return result.data[0]

    def latest(self, org_id: str, report_type: str) -> Optional[dict]:
        result = (
            self._db.table("reports")
            .select("*")
            .eq("org_id", org_id)
            .eq("type", report_type)
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        return result.data
