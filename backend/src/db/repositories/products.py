from typing import Optional
from src.db.client import get_supabase
from .base import BaseRepo


class ProductRepo(BaseRepo):
    def __init__(self):
        self._db = get_supabase()

    def get_by_id(self, org_id: str, product_id: str) -> Optional[dict]:
        result = self._exec(
            self._db.table("products")
            .select("*")
            .eq("org_id", org_id)
            .eq("id", product_id)
            .maybe_single()
        )
        return result.data if result else None

    def list_by_org(self, org_id: str) -> list[dict]:
        result = self._exec(
            self._db.table("products")
            .select("*")
            .eq("org_id", org_id)
            .order("name")
        )
        return result.data if result else []

    def create(self, org_id: str, name: str, unit_price: float,
               description: Optional[str] = None, stock_qty: Optional[int] = None) -> dict:
        result = self._exec(
            self._db.table("products")
            .insert({
                "org_id": org_id,
                "name": name,
                "description": description,
                "unit_price": unit_price,
                "stock_qty": stock_qty,
            })
        )
        return result.data[0] if result and result.data else {}

    def update(self, org_id: str, product_id: str,
               name: Optional[str] = None, unit_price: Optional[float] = None,
               description: Optional[str] = None, stock_qty: Optional[int] = None) -> Optional[dict]:
        payload = {}
        if name is not None:
            payload["name"] = name
        if unit_price is not None:
            payload["unit_price"] = unit_price
        if description is not None:
            payload["description"] = description
        if stock_qty is not None:
            payload["stock_qty"] = stock_qty
        if not payload:
            return self.get_by_id(org_id, product_id)
        result = self._exec(
            self._db.table("products")
            .update(payload)
            .eq("org_id", org_id)
            .eq("id", product_id)
        )
        return result.data[0] if result and result.data else None

    def delete(self, org_id: str, product_id: str) -> bool:
        result = self._exec(
            self._db.table("products")
            .delete()
            .eq("org_id", org_id)
            .eq("id", product_id)
        )
        return len(result.data) > 0 if result else False
