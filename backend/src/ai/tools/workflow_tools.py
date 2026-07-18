"""Workflow tools — multi-step business operations built on top of the
existing jobs queue + repos. Each tool is a thin orchestrator that the
LLM can call as a single function call rather than chaining primitives.

Examples:
- `workflow_trigger_inbound_reply` — full inbound WhatsApp flow: upsert
  contact → open conversation → run Maya → save reply → optionally
  enqueue a quotation job.
- `workflow_generate_quotation` — pull lead + items, compute totals,
  insert quotation row, enqueue PDF generation.
- `workflow_daily_briefing` — enqueue the morning briefing job.
- `workflow_list_runs` — list recent workflow executions for the dashboard.
"""

import json
import time
import uuid
from typing import Optional

from crewai.tools import tool

from src.core.config import logger
from src.db.repositories.contacts import ContactRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.jobs import JobRepo
from src.db.repositories.leads import LeadRepo
from src.db.repositories.quotations import QuotationRepo
from src.db.repositories.products import ProductRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


def _safe_json(obj, limit: int = 4000) -> str:
    try:
        s = json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        s = str(obj)
    if len(s) > limit:
        s = s[:limit] + "... [truncated]"
    return s


@tool("Workflow Trigger Inbound Reply")
def workflow_trigger_inbound_reply_tool(
    phone: str, body: str, channel_id: str,
    name: Optional[str] = None, source: str = "whatsapp",
) -> str:
    """End-to-end workflow for an inbound WhatsApp message: ensures the
    contact exists, opens/uses a conversation, enqueues the AI reply job,
    and returns the conversation id. Use this as the single entry point
    when a new WhatsApp message arrives — the worker takes over from
    here. Returns the conversation_id and the queued job id so the
    caller can poll for status."""
    try:
        contact = ContactRepo().upsert(ORG_ID, phone, name=name, source=source)
        conv = ConversationRepo().get_open_by_contact(ORG_ID, phone)
        if not conv:
            conv = ConversationRepo().create(ORG_ID, contact["id"], channel_id)
        job = JobRepo().enqueue(ORG_ID, "process_inbound", payload={
            "conversation_id": conv["id"],
            "from_number": phone,
            "body": body,
            "channel_id": channel_id,
        })
        return _safe_json({
            "contact_id": contact["id"],
            "conversation_id": conv["id"],
            "job_id": job["id"],
        })
    except Exception as e:
        logger.error(f"workflow_trigger_inbound_reply_tool failed: {e}", exc_info=True)
        return f"Error: {e}"


@tool("Workflow Generate Quotation")
def workflow_generate_quotation_tool(
    lead_id: str, items: list[dict], tax_rate: float = 0.0,
    currency: str = "MYR", valid_until: Optional[str] = None,
) -> str:
    """End-to-end quotation workflow: looks up product prices, computes
    subtotal/tax/total, persists a `quotations` row in
    `pending_approval` status, and enqueues a `generate_quotation` job
    to render the PDF. `items` is a list of {name, qty} (or {product_id,
    qty}) — unknown names are reported back. Use this whenever the AI
    decides a quotation is needed (e.g. Maya's needs_quotation=true)."""
    try:
        products = {p["name"].lower(): p for p in ProductRepo().list_by_org(ORG_ID)}
        line_rows: list[dict] = []
        missing: list[str] = []
        for raw in items:
            qty = int(raw.get("qty", 1) or 1)
            key = (raw.get("name") or "").lower()
            product = products.get(key)
            if not product:
                missing.append(raw.get("name", "?"))
                continue
            unit_price = float(product["unit_price"])
            line_rows.append({
                "description": product["name"],
                "qty": qty,
                "unit_price": unit_price,
                "line_total": round(unit_price * qty, 2),
                "product_id": product.get("id"),
            })
        if not line_rows:
            return f"Error: none of the requested items are in the catalogue. Missing: {missing}"
        subtotal = round(sum(r["line_total"] for r in line_rows), 2)
        tax = round(subtotal * float(tax_rate), 2)
        total = round(subtotal + tax, 2)
        number = f"Q-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        q = QuotationRepo().create(
            ORG_ID, lead_id=lead_id, number=number,
            subtotal=subtotal, tax=tax, total=total,
            currency=currency, valid_until=valid_until,
        )
        for row in line_rows:
            QuotationRepo().add_item(
                q["id"], description=row["description"], qty=row["qty"],
                unit_price=row["unit_price"], line_total=row["line_total"],
                product_id=row.get("product_id"),
            )
        job = JobRepo().enqueue(ORG_ID, "generate_quotation", payload={
            "quotation_id": q["id"],
            "lead_id": lead_id,
        })
        return _safe_json({
            "quotation": q,
            "items": line_rows,
            "missing": missing,
            "job_id": job["id"],
        })
    except Exception as e:
        logger.error(f"workflow_generate_quotation_tool failed: {e}", exc_info=True)
        return f"Error: {e}"


@tool("Workflow Trigger Daily Briefing")
def workflow_trigger_daily_briefing_tool(run_at: Optional[str] = None) -> str:
    """Enqueue the morning daily-briefing job. Without `run_at` the worker
    runs it immediately. Use this when the AI detects a reminder trigger
    (e.g. "kirim laporan pagi ni") or for manual scheduling from the
    dashboard. Returns the job id."""
    try:
        job = JobRepo().enqueue(ORG_ID, "daily_briefing", payload={}, run_at=run_at)
        return _safe_json({"job_id": job["id"], "run_at": job.get("run_at")})
    except Exception as e:
        return f"Error: {e}"


@tool("Workflow Lead Pipeline Summary")
def workflow_lead_pipeline_summary_tool() -> str:
    """Return a one-shot pipeline summary: counts by lead score
    (hot/warm/cold), top 5 hot leads, and the most recent 5 lead
    updates. Use this when the user asks "how's the pipeline?" or for
    the morning briefing."""
    try:
        leads = LeadRepo().list_by_org(ORG_ID)
        counts: dict[str, int] = {"hot": 0, "warm": 0, "cold": 0}
        for ld in leads:
            sc = (ld.get("score") or "cold").lower()
            if sc in counts:
                counts[sc] += 1
        hot_top = sorted(
            [ld for ld in leads if (ld.get("score") or "").lower() == "hot"],
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )[:5]
        recent = sorted(leads, key=lambda x: x.get("updated_at", ""), reverse=True)[:5]
        return _safe_json({"counts": counts, "hot_top": hot_top, "recent": recent})
    except Exception as e:
        return f"Error: {e}"


@tool("Workflow Schedule Job")
def workflow_schedule_job_tool(
    job_type: str, payload: Optional[dict] = None, run_at: Optional[str] = None,
) -> str:
    """Generic job scheduler. `job_type` is one of "process_inbound",
    "generate_quotation", "daily_briefing", or any custom type your
    worker knows how to handle. `run_at` is an ISO 8601 datetime
    string for delayed execution. Use this for one-off scheduled
    tasks that don't have a dedicated workflow tool."""
    try:
        job = JobRepo().enqueue(ORG_ID, job_type, payload=payload, run_at=run_at)
        return _safe_json({"job_id": job["id"], "type": job_type, "run_at": job.get("run_at")})
    except Exception as e:
        return f"Error: {e}"
