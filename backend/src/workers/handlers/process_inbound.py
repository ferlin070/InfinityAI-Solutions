from src.core.config import logger
from src.db.repositories.contacts import ContactRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.messages import MessageRepo
from src.db.repositories.leads import LeadRepo
from src.db.repositories.products import ProductRepo
from src.db.repositories.jobs import JobRepo
from src.channels.wa_webjs import WAWebJSProvider
from src.ai.flows.inbound_conversation_flow import InboundConversationFlow

ORG_ID = "00000000-0000-0000-0000-000000000001"


def process_inbound(job: dict) -> None:
    payload = job.get("payload", {})
    channel_id = payload["channel_id"]
    from_number = payload["from"]
    body = payload.get("body", "")
    message_id = payload.get("message_id", "")

    contact_repo = ContactRepo()
    conv_repo = ConversationRepo()
    msg_repo = MessageRepo()
    lead_repo = LeadRepo()
    product_repo = ProductRepo()

    contact = contact_repo.get_by_phone(ORG_ID, from_number)
    if not contact:
        contact = contact_repo.upsert(ORG_ID, from_number, source="whatsapp")

    conversation = conv_repo.get_open_by_contact(ORG_ID, contact["id"])
    if not conversation:
        conversation = conv_repo.create(ORG_ID, contact["id"], channel_id)

    msg_repo.create(
        org_id=ORG_ID,
        conversation_id=conversation["id"],
        direction="inbound",
        sender="customer",
        body=body,
        external_id=message_id,
        channel_id=channel_id,
    )

    last_msgs = msg_repo.list_by_conversation(ORG_ID, conversation["id"], limit=20)
    lead = lead_repo.get_by_contact(ORG_ID, contact["id"])
    products = product_repo.list_by_org(ORG_ID)

    flow = InboundConversationFlow(
        conversation_id=conversation["id"],
        last_messages=last_msgs,
        lead_profile=lead,
        products=products,
        phone_number=from_number,
        org_id=ORG_ID,
    )
    flow.kickoff()

    reply = flow._state.get("reply", "")
    intent = flow._state.get("intent", "unclear")
    lead_score = flow._state.get("lead_score", "cold")
    score_reason = flow._state.get("score_reason", "")

    if intent == "unclear":
        conv_repo.set_mode(ORG_ID, conversation["id"], "human")
        reply = reply or (
            "Maaf, saya kurang pasti dengan permintaan anda. "
            "Saya akan hubungkan anda dengan staff kami."
        )

    lead_repo.upsert(
        ORG_ID, contact["id"],
        score=lead_score,
        status="new" if not lead else lead.get("status", "new"),
        interest_summary=body[:200],
        score_reason=score_reason,
    )

    channel = WAWebJSProvider()
    if reply:
        try:
            channel.send_text(channel_id, from_number, reply)
        except Exception as send_err:
            logger.warning(
                f"[process_inbound] Failed to send reply (non-fatal): {send_err}. "
                f"Conversation {conversation['id']} still created."
            )

    if flow._state.get("quotation_needed"):
        items = flow._state.get("quotation_items", [])
        if items:
            job_repo = JobRepo()
            job_repo.enqueue(
                ORG_ID,
                "generate_quotation",
                payload={
                    "conversation_id": conversation["id"],
                    "lead_id": lead["id"] if lead else None,
                    "contact_id": contact["id"],
                    "items": items,
                    "channel_id": channel_id,
                    "from_number": from_number,
                },
            )

    logger.info(
        f"Inbound processed: contact={contact['id']} "
        f"conversation={conversation['id']} intent={intent} score={lead_score}"
    )
