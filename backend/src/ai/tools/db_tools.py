"""Database tools — wrappers over the existing `src/db/repositories/*` layer so
agents can do more than read: create/update contacts, score leads, create
quotations, enqueue jobs, etc. Each tool follows the existing
`@tool("Name") -> str` pattern in `src/ai/tools/`.

Read-only lookups (single contact, single lead) are intentionally kept in the
narrower tools in `contact_info.py` / `conversation_history.py` — these are
the "expanded" tools for batch operations and writes.
"""

import json
from typing import Optional

from crewai.tools import tool

from src.core.config import logger
from src.db.repositories.contacts import ContactRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.leads import LeadRepo
from src.db.repositories.messages import MessageRepo
from src.db.repositories.products import ProductRepo
from src.db.repositories.quotations import QuotationRepo
from src.db.repositories.jobs import JobRepo
from src.db.repositories.channels import ChannelRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


def _safe_json(obj, limit: int = 4000) -> str:
    try:
        s = json.dumps(obj, default=str, ensure_ascii=False)
    except Exception:
        s = str(obj)
    if len(s) > limit:
        s = s[:limit] + "... [truncated]"
    return s


# ─── Contacts ──────────────────────────────────────────────────────────────

@tool("DB List Contacts")
def db_list_contacts_tool(limit: int = 50, source: Optional[str] = None) -> str:
    """List contacts in the CRM, most recent first. Optionally filter by
    `source` (e.g. "whatsapp", "facebook"). Returns a JSON array of contact
    records (name, phone, source, tags, created_at). Use this for batch CRM
    inspection — for a single contact lookup prefer the Contact Info tool."""
    try:
        repo = ContactRepo()
        rows = repo.list_by_org(ORG_ID)[: max(1, min(limit, 500))]
        if source:
            rows = [r for r in rows if r.get("source") == source]
        return _safe_json(rows)
    except Exception as e:
        return f"Error listing contacts: {e}"


@tool("DB Upsert Contact")
def db_upsert_contact_tool(
    phone: str, name: Optional[str] = None, source: str = "whatsapp",
    tags: Optional[list[str]] = None,
) -> str:
    """Create or update a contact by phone number. Use this to record a new
    WhatsApp lead or to update the name/tags after a conversation. Returns
    the saved contact record."""
    try:
        repo = ContactRepo()
        return _safe_json(repo.upsert(ORG_ID, phone, name=name, source=source, tags=tags))
    except Exception as e:
        return f"Error upserting contact: {e}"


@tool("DB Update Contact Tags")
def db_update_contact_tags_tool(contact_id: str, tags: list[str]) -> str:
    """Replace the tag list on an existing contact by id. Use after a call to
    add or remove a tag (e.g. ["vip"], ["interested-package-a"], ["follow-up"])."""
    try:
        repo = ContactRepo()
        return _safe_json(repo.update_tags(ORG_ID, contact_id, tags))
    except Exception as e:
        return f"Error updating tags: {e}"


# ─── Leads ─────────────────────────────────────────────────────────────────

@tool("DB List Leads")
def db_list_leads_tool(score_filter: Optional[str] = None, limit: int = 50) -> str:
    """List leads in the CRM, most recently updated first. Optionally filter
    by `score` ("hot", "warm", "cold"). Each lead is returned together with
    its joined contact record so you can see the name/phone alongside the
    score and interest summary. Use this for daily pipeline review."""
    try:
        repo = LeadRepo()
        rows = repo.list_by_org(ORG_ID, score_filter=score_filter)[: max(1, min(limit, 500))]
        return _safe_json(rows)
    except Exception as e:
        return f"Error listing leads: {e}"


@tool("DB Upsert Lead")
def db_upsert_lead_tool(
    contact_id: str, score: str = "cold", status: str = "new",
    interest_summary: Optional[str] = None, score_reason: Optional[str] = None,
) -> str:
    """Create or update a lead record for a contact. `score` must be one of
    "hot", "warm", "cold". `status` is the pipeline stage (e.g. "new",
    "qualified", "negotiation", "won", "lost"). `interest_summary` is a
    short free-text description of what the lead wants. Use this whenever
    the AI classifies a new lead or updates an existing one after a
    conversation."""
    try:
        repo = LeadRepo()
        return _safe_json(repo.upsert(
            ORG_ID, contact_id,
            score=score, status=status,
            interest_summary=interest_summary,
            score_reason=score_reason,
        ))
    except Exception as e:
        return f"Error upserting lead: {e}"


# ─── Products ──────────────────────────────────────────────────────────────

@tool("DB List Products")
def db_list_products_tool(limit: int = 200) -> str:
    """List all products in the catalogue with their prices and stock. Returns
    a JSON array sorted by name. Use this for catalogue-level operations
    (e.g. building a price sheet, checking stock across the full range)."""
    try:
        repo = ProductRepo()
        rows = repo.list_by_org(ORG_ID)[: max(1, min(limit, 1000))]
        return _safe_json(rows)
    except Exception as e:
        return f"Error listing products: {e}"


@tool("DB Search Products")
def db_search_products_tool(query: str, limit: int = 20) -> str:
    """Search the product catalogue by a free-text query. Matches against
    name and description (case-insensitive). Returns up to `limit` matching
    products with name, price, and stock. Use this when the user asks "do
    we have anything like X?" — for a known product name use Product
    Pricing instead."""
    try:
        repo = ProductRepo()
        q = (query or "").lower().strip()
        if not q:
            return "Error: query is required."
        all_products = repo.list_by_org(ORG_ID)
        matches = [
            p for p in all_products
            if q in (p.get("name", "") or "").lower()
            or q in (p.get("description", "") or "").lower()
        ][: max(1, min(limit, 100))]
        return _safe_json(matches) or f"No products matched '{query}'."
    except Exception as e:
        return f"Error searching products: {e}"


@tool("DB Create Product")
def db_create_product_tool(
    name: str, unit_price: float,
    description: Optional[str] = None, stock_qty: Optional[int] = None,
) -> str:
    """Add a new product to the catalogue. `unit_price` is in MYR. Use this
    when the user wants to onboard a new SKU into the system."""
    try:
        repo = ProductRepo()
        return _safe_json(repo.create(
            ORG_ID, name=name, unit_price=unit_price,
            description=description, stock_qty=stock_qty,
        ))
    except Exception as e:
        return f"Error creating product: {e}"


# ─── Quotations ────────────────────────────────────────────────────────────

@tool("DB Create Quotation")
def db_create_quotation_tool(
    lead_id: str, number: str, subtotal: float, tax: float, total: float,
    currency: str = "MYR", valid_until: Optional[str] = None,
) -> str:
    """Create a new quotation (sebut harga) for a lead, in "pending_approval"
    status. `subtotal`, `tax`, and `total` are floats. Use the Job system
    afterwards to actually generate the PDF."""
    try:
        repo = QuotationRepo()
        return _safe_json(repo.create(
            ORG_ID, lead_id=lead_id, number=number,
            subtotal=subtotal, tax=tax, total=total,
            currency=currency, valid_until=valid_until,
        ))
    except Exception as e:
        return f"Error creating quotation: {e}"


@tool("DB Approve Quotation")
def db_approve_quotation_tool(quotation_id: str, approved_by: str) -> str:
    """Move a quotation from "pending_approval" to "sent". Use this after a
    human approves a quote. `approved_by` is the user/admin who approved
    (email or id)."""
    try:
        repo = QuotationRepo()
        return _safe_json(repo.approve(ORG_ID, quotation_id, approved_by))
    except Exception as e:
        return f"Error approving quotation: {e}"


@tool("DB List Pending Quotations")
def db_list_pending_quotations_tool(limit: int = 50) -> str:
    """List quotations currently in "pending_approval" status, joined with
    their lead and contact. Use for the approval queue."""
    try:
        repo = QuotationRepo()
        rows = repo.list_pending_approval(ORG_ID)[: max(1, min(limit, 200))]
        return _safe_json(rows)
    except Exception as e:
        return f"Error listing quotations: {e}"


# ─── Jobs (workflow queue) ─────────────────────────────────────────────────

@tool("DB Enqueue Job")
def db_enqueue_job_tool(job_type: str, payload: Optional[dict] = None,
                        run_at: Optional[str] = None) -> str:
    """Enqueue a background job of the given type. Supported types:
    "process_inbound" (handle a WhatsApp message), "generate_quotation"
    (build a PDF), "daily_briefing" (run the morning report). `payload`
    is a free-form dict specific to the job type. `run_at` is an optional
    ISO 8601 datetime string for delayed execution. The job will be
    picked up by the worker process. Use this to trigger workflows
    asynchronously without blocking the current response."""
    try:
        repo = JobRepo()
        return _safe_json(repo.enqueue(ORG_ID, job_type, payload=payload, run_at=run_at))
    except Exception as e:
        return f"Error enqueuing job: {e}"


# ─── Conversations / Messages ──────────────────────────────────────────────

@tool("DB List Open Conversations")
def db_list_open_conversations_tool(limit: int = 50) -> str:
    """List all open conversations, most recently updated first, with their
    joined contact. Use this for a live inbox view or to find conversations
    that need follow-up."""
    try:
        repo = ConversationRepo()
        rows = repo.list_open(ORG_ID)[: max(1, min(limit, 200))]
        return _safe_json(rows)
    except Exception as e:
        return f"Error listing conversations: {e}"


@tool("DB Create Conversation")
def db_create_conversation_tool(contact_id: str, channel_id: str) -> str:
    """Open a new conversation for a contact on a given channel. Returns
    the new conversation id. Use this when an inbound message arrives from
    a contact that has no open conversation yet."""
    try:
        repo = ConversationRepo()
        return _safe_json(repo.create(ORG_ID, contact_id, channel_id))
    except Exception as e:
        return f"Error creating conversation: {e}"


@tool("DB Save Message")
def db_save_message_tool(
    conversation_id: str, direction: str, sender: str,
    body: Optional[str] = None, media_url: Optional[str] = None,
    external_id: Optional[str] = None,
) -> str:
    """Persist a single message to a conversation. `direction` is "in" or
    "out", `sender` is "customer" / "agent" / "ai". `external_id` is the
    channel's message id (e.g. WhatsApp message id) for dedup. Use this
    to record AI-generated replies or to backfill inbound messages."""
    try:
        repo = MessageRepo()
        return _safe_json(repo.create(
            ORG_ID, conversation_id, direction, sender,
            body=body, media_url=media_url, external_id=external_id,
        ))
    except Exception as e:
        return f"Error saving message: {e}"


# ─── Channels ──────────────────────────────────────────────────────────────

@tool("DB List Channels")
def db_list_channels_tool() -> str:
    """List WhatsApp channels configured for this organisation, with their
    status (pending_qr / connected / disconnected). Use this to check
    which channels are online before sending."""
    try:
        repo = ChannelRepo()
        return _safe_json(repo.list_by_org(ORG_ID))
    except Exception as e:
        return f"Error listing channels: {e}"
