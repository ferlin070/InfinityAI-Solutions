import os
import hmac
from fastapi import APIRouter, HTTPException, Request
from src.core.config import logger
from src.db.repositories.jobs import JobRepo
from src.db.repositories.messages import MessageRepo
from src.db.repositories.channels import ChannelRepo
from src.channels.wa_webjs import WAWebJSProvider

router = APIRouter()
GATEWAY_SECRET = os.getenv("GATEWAY_SHARED_SECRET", "dev-secret-change-in-production")


@router.post("/webhooks/wa-gateway")
async def wa_gateway_webhook(request: Request):
    secret = request.headers.get("X-Gateway-Secret", "")
    if not hmac.compare_digest(secret, GATEWAY_SECRET):
        raise HTTPException(status_code=401, detail="Invalid gateway secret")

    payload = await request.json()
    provider = WAWebJSProvider()
    msg = provider.parse_inbound(payload)

    channel_repo = ChannelRepo()
    channel = channel_repo.get_by_id("00000000-0000-0000-0000-000000000001", msg.channel_id)
    if not channel:
        ch = {
            "id": msg.channel_id,
            "org_id": "00000000-0000-0000-0000-000000000001",
            "type": "wa_webjs",
            "phone_number": msg.from_number,
            "status": "connected",
        }
        channel_repo._db.table("channels").upsert(ch, on_conflict="id").execute()

    msg_repo = MessageRepo()
    existing = msg_repo.get_by_external_id(msg.channel_id, msg.message_id)
    if existing:
        return {"status": "duplicate"}

    msg_repo.create(
        org_id="00000000-0000-0000-0000-000000000001",
        conversation_id="",  # set by process_inbound handler
        direction="inbound",
        sender="customer",
        body=msg.body,
        external_id=msg.message_id,
        channel_id=msg.channel_id,
    )

    job_repo = JobRepo()
    job_repo.enqueue(
        org_id="00000000-0000-0000-0000-000000000001",
        job_type="process_inbound",
        payload={
            "channel_id": msg.channel_id,
            "from": msg.from_number,
            "body": msg.body,
            "message_id": msg.message_id,
            "timestamp": msg.timestamp,
        },
    )

    return {"status": "ok"}
