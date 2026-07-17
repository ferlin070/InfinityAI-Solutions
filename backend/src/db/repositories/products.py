from typing import Optional
from src.db.client import get_supabase


class ProductRepo:
    def __init__(self):
        self._db = get_supabase()

    def get_by_id(self, org_id: str, product_id: str) -> Optional[dict]:
        result = (
            self._db.table("products")
            .select("*")
            .eq("org_id", org_id)
            .eq("id", product_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def list_by_org(self, org_id: str) -> list[dict]:
        result = (
            self._db.table("products")
            .select("*")
            .eq("org_id", org_id)
            .order("name")
            .execute()
        )
        return result.data

    def create(self, org_id: str, name: str, unit_price: float,
               description: Optional[str] = None, stock_qty: Optional[int] = None) -> dict:
        result = (
            self._db.table("products")
            .insert({
                "org_id": org_id,
                "name": name,
                "description": description,
                "unit_price": unit_price,
                "stock_qty": stock_qty,
            })
            .execute()
        )
        return result.data[0]
