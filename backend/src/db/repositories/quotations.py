from typing import Optional
from src.db.client import get_supabase


class QuotationRepo:
    def __init__(self):
        self._db = get_supabase()

    def create(self, org_id: str, lead_id: str, number: str, subtotal: float,
               tax: float, total: float, currency: str = "MYR",
               valid_until: Optional[str] = None) -> dict:
        result = (
            self._db.table("quotations")
            .insert({
                "org_id": org_id,
                "lead_id": lead_id,
                "number": number,
                "status": "pending_approval",
                "currency": currency,
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "valid_until": valid_until,
            })
            .execute()
        )
        return result.data[0]

    def add_item(self, quotation_id: str, description: str, qty: int,
                 unit_price: float, line_total: float,
                 product_id: Optional[str] = None) -> dict:
        payload = {
            "quotation_id": quotation_id,
            "description": description,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
        }
        if product_id is not None:
            payload["product_id"] = product_id
        result = (
            self._db.table("quotation_items")
            .insert(payload)
            .execute()
        )
        return result.data[0]

    def approve(self, org_id: str, quotation_id: str, approved_by: str) -> dict:
        result = (
            self._db.table("quotations")
            .update({"status": "sent", "approved_by": approved_by})
            .eq("org_id", org_id)
            .eq("id", quotation_id)
            .execute()
        )
        return result.data[0]

    def get_with_items(self, org_id: str, quotation_id: str) -> Optional[dict]:
        q = (
            self._db.table("quotations")
            .select("*, quotation_items(*)")
            .eq("org_id", org_id)
            .eq("id", quotation_id)
            .maybe_single()
            .execute()
        )
        return q.data

    def list_pending_approval(self, org_id: str) -> list[dict]:
        result = (
            self._db.table("quotations")
            .select("*, leads(*, contacts(*))")
            .eq("org_id", org_id)
            .eq("status", "pending_approval")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
