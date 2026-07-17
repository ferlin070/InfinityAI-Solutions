from typing import Optional

from crewai.tools import tool
from src.db.repositories.products import ProductRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


@tool("Product Pricing")
def product_pricing_tool(product_name: str) -> str:
    """Look up product pricing from the database by product name.
    Returns the price and description if found. Use this tool whenever
    you need to quote a price — never invent prices."""
    try:
        repo = ProductRepo()
        products = repo.list_by_org(ORG_ID)
        for p in products:
            if product_name.lower() in p["name"].lower():
                stock = f" (Stok: {p['stock_qty']})" if p.get("stock_qty") is not None else ""
                return f"{p['name']}: RM{p['unit_price']:.2f}{stock}"
        return f"Product '{product_name}' not found in catalogue."
    except Exception as e:
        return f"Error looking up product: {e}"
