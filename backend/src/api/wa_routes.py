import asyncio

from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel

from src.db.repositories.products import ProductRepo
from src.ai.agents.config_store import AgentOverride, get_agent_config_store
from src.ai.agents.registry import load_agent, load_agents
from src.channels.wa_webjs import WAWebJSProvider
from src.core.config import logger
from src.core.constants import AGENTS
from src.core.sessions import verify_session
from src.db.repositories.channels import ChannelRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.leads import LeadRepo
from src.db.repositories.messages import MessageRepo
from src.db.repositories.quotations import QuotationRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"
router = APIRouter()


def require_session(session_token: str | None):
    if not verify_session(session_token):
        raise HTTPException(status_code=401, detail="Sesi tamat. Sila log masuk semula.")


class SendMessageRequest(BaseModel):
    body: str
    channel_id: str
    to: str


class ApproveQuotationRequest(BaseModel):
    approved_by: str = "Bos"


class CreateChannelRequest(BaseModel):
    phone_number: str


class UpdateAgentConfigRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    role: str | None = None
    goal: str | None = None
    backstory: str | None = None


class CreateProductRequest(BaseModel):
    name: str
    unit_price: float
    description: str | None = None
    stock_qty: int | None = None


class UpdateProductRequest(BaseModel):
    name: str | None = None
    unit_price: float | None = None
    description: str | None = None
    stock_qty: int | None = None


class UpdateBusinessProfileRequest(BaseModel):
    company_name: str | None = None
    industry: str | None = None
    description: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None


# ─── Channels (WhatsApp Connection) ────────────────────────────


@router.get("/api/channels")
async def list_channels(session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ChannelRepo()
    return repo.list_by_org(ORG_ID)


@router.post("/api/channels")
async def create_channel(data: CreateChannelRequest,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ChannelRepo()
    provider = WAWebJSProvider()

    channel = repo.create(ORG_ID, data.phone_number)
    # provider.start_session() is a blocking `requests` call — offload it so a
    # slow/unreachable gateway (e.g. not deployed yet) can't stall the single
    # asyncio event loop for its whole timeout, which would freeze every other
    # request the server is handling (including unrelated /api/chat/stream
    # SSE responses) for as long as this one blocking call is stuck.
    await asyncio.to_thread(provider.start_session, channel["id"])
    logger.info(f"Channel created: {channel['id']} ({data.phone_number})")
    return channel


@router.get("/api/channels/{channel_id}/qr")
async def get_channel_qr(channel_id: str,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    provider = WAWebJSProvider()
    return await asyncio.to_thread(provider.get_qr, channel_id)


@router.get("/api/channels/{channel_id}/status")
async def get_channel_status(channel_id: str,
                             session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ChannelRepo()
    provider = WAWebJSProvider()

    gateway_status = await asyncio.to_thread(provider.get_session_status, channel_id)
    repo.update_status(ORG_ID, channel_id, gateway_status)
    return {"channel_id": channel_id, "status": gateway_status}


@router.post("/api/channels/{channel_id}/disconnect")
@router.delete("/api/channels/{channel_id}")
async def delete_channel(channel_id: str,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ChannelRepo()
    provider = WAWebJSProvider()
    await asyncio.to_thread(provider.destroy_session, channel_id)
    repo.delete(ORG_ID, channel_id)
    logger.info(f"Channel deleted: {channel_id}")
    return {"status": "deleted"}


# ─── Conversations ──────────────────────────────────────────────


@router.get("/api/conversations")
async def list_conversations(status: str | None = None,
                             session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ConversationRepo()
    if status:
        return repo.list_open(ORG_ID) if status == "open" else []
    return repo.list_open(ORG_ID)


@router.get("/api/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, limit: int = 20,
                       session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = MessageRepo()
    return repo.list_by_conversation(ORG_ID, conv_id, limit=limit)


@router.post("/api/conversations/{conv_id}/takeover")
async def takeover_conversation(conv_id: str,
                                session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ConversationRepo()
    result = repo.set_mode(ORG_ID, conv_id, "human")
    logger.info(f"Staff took over conversation {conv_id}")
    return {"status": "ok", "mode": "human"}


@router.post("/api/conversations/{conv_id}/send")
async def send_message(conv_id: str, data: SendMessageRequest,
                       session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ConversationRepo()
    msg_repo = MessageRepo()

    conv = repo.list_open(ORG_ID)
    conv = next((c for c in conv if c["id"] == conv_id), None)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_repo.create(
        org_id=ORG_ID,
        conversation_id=conv_id,
        direction="outbound",
        sender="staff",
        body=data.body,
    )

    channel = WAWebJSProvider()
    await asyncio.to_thread(channel.send_text, data.channel_id, data.to, data.body)

    return {"status": "sent"}


# ─── Leads ──────────────────────────────────────────────────────


@router.get("/api/leads")
async def list_leads(score: str | None = None,
                     session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = LeadRepo()
    return repo.list_by_org(ORG_ID, score_filter=score)


# ─── Quotations ─────────────────────────────────────────────────


@router.get("/api/quotations")
async def list_quotations(status: str | None = None,
                          session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = QuotationRepo()
    if status:
        if status == "pending_approval":
            return repo.list_pending_approval(ORG_ID)
        return []
    return repo.list_pending_approval(ORG_ID)


@router.post("/api/quotations/{quote_id}/approve")
async def approve_quotation(quote_id: str, data: ApproveQuotationRequest,
                            session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = QuotationRepo()
    result = repo.approve(ORG_ID, quote_id, data.approved_by)
    logger.info(f"Quotation {quote_id} approved by {data.approved_by}")
    return {"status": "approved", "quotation": result}


# ─── Agent Config ────────────────────────────────────────────────


@router.get("/api/agents")
async def list_agents(session_token: str | None = Cookie(None)):
    require_session(session_token)
    configs = load_agents(ORG_ID)
    return [
        {
            "key": cfg.key,
            "name": cfg.name,
            "role": cfg.role,
            "goal": cfg.goal,
            "backstory": cfg.backstory,
            "provider": cfg.provider,
            "model": cfg.model,
        }
        for cfg in configs.values()
    ]


# ─── Products ────────────────────────────────────────────────────


@router.get("/api/products")
async def list_products(session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ProductRepo()
    return repo.list_by_org(ORG_ID)


@router.post("/api/products")
async def create_product(data: CreateProductRequest,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ProductRepo()
    product = repo.create(
        org_id=ORG_ID,
        name=data.name,
        unit_price=data.unit_price,
        description=data.description,
        stock_qty=data.stock_qty,
    )
    logger.info(f"Product created: {product['id']} ({data.name})")
    return product


@router.put("/api/products/{product_id}")
async def update_product(product_id: str, data: UpdateProductRequest,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ProductRepo()
    product = repo.update(
        org_id=ORG_ID,
        product_id=product_id,
        name=data.name,
        unit_price=data.unit_price,
        description=data.description,
        stock_qty=data.stock_qty,
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    logger.info(f"Product updated: {product_id}")
    return product


@router.delete("/api/products/{product_id}")
async def delete_product(product_id: str,
                         session_token: str | None = Cookie(None)):
    require_session(session_token)
    repo = ProductRepo()
    deleted = repo.delete(ORG_ID, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    logger.info(f"Product deleted: {product_id}")
    return {"status": "deleted"}


# ─── Business Profile ────────────────────────────────────────────


def _build_profile_response(org: dict) -> dict:
    settings = org.get("settings", {}) or {}
    return {
        "company_name": org.get("name", ""),
        "industry": settings.get("industry", ""),
        "description": settings.get("description", ""),
        "address": settings.get("address", ""),
        "phone": settings.get("phone", ""),
        "email": settings.get("email", ""),
        "website": settings.get("website", ""),
        "logo_url": settings.get("logo_url", ""),
    }


@router.get("/api/business/profile")
async def get_business_profile(session_token: str | None = Cookie(None)):
    require_session(session_token)
    from src.db.client import get_supabase
    db = get_supabase()
    result = db.table("organizations").select("*").eq("id", ORG_ID).maybe_single().execute()
    org = result.data
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _build_profile_response(org)


@router.put("/api/business/profile")
async def update_business_profile(data: UpdateBusinessProfileRequest,
                                  session_token: str | None = Cookie(None)):
    require_session(session_token)
    from src.db.client import get_supabase
    db = get_supabase()
    result = db.table("organizations").select("settings").eq("id", ORG_ID).maybe_single().execute()
    org = result.data
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    settings = org.get("settings", {}) or {}
    updates = {}
    for field in ("industry", "description", "address", "phone", "email", "website", "logo_url"):
        val = getattr(data, field, None)
        if val is not None:
            settings[field] = val
    if data.company_name is not None:
        updates["name"] = data.company_name
    updates["settings"] = settings
    db.table("organizations").update(updates).eq("id", ORG_ID).execute()
    logger.info(f"Business profile updated for org {ORG_ID}")
    org_updated = db.table("organizations").select("*").eq("id", ORG_ID).maybe_single().execute()
    return _build_profile_response(org_updated.data or org)


@router.get("/api/agents/{agent_key}")
async def get_agent_config(agent_key: str,
                           session_token: str | None = Cookie(None)):
    require_session(session_token)
    try:
        cfg = load_agent(agent_key, ORG_ID)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_key}'")
    return {
        "key": cfg.key,
        "name": cfg.name,
        "role": cfg.role,
        "goal": cfg.goal,
        "backstory": cfg.backstory,
        "provider": cfg.provider,
        "model": cfg.model,
    }


@router.put("/api/agents/{agent_key}")
async def update_agent_config(agent_key: str, data: UpdateAgentConfigRequest,
                              session_token: str | None = Cookie(None)):
    require_session(session_token)
    key = agent_key.upper()
    if key not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_key}'")
    store = get_agent_config_store()
    store.set(ORG_ID, key, AgentOverride(
        provider=data.provider,
        model=data.model,
        role=data.role,
        goal=data.goal,
        backstory=data.backstory,
    ))
    cfg = load_agent(key, ORG_ID)
    logger.info(f"Agent config updated: {key} model={cfg.model}")
    return {
        "key": cfg.key,
        "name": cfg.name,
        "role": cfg.role,
        "goal": cfg.goal,
        "backstory": cfg.backstory,
        "provider": cfg.provider,
        "model": cfg.model,
    }


@router.delete("/api/agents/{agent_key}")
async def reset_agent_config(agent_key: str,
                             session_token: str | None = Cookie(None)):
    require_session(session_token)
    key = agent_key.upper()
    if key not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_key}'")
    store = get_agent_config_store()
    store.delete(ORG_ID, key)
    cfg = load_agent(key, ORG_ID)
    logger.info(f"Agent config reset to default: {key}")
    return {
        "key": cfg.key,
        "name": cfg.name,
        "role": cfg.role,
        "goal": cfg.goal,
        "backstory": cfg.backstory,
        "provider": cfg.provider,
        "model": cfg.model,
    }
