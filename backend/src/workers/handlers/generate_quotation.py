import os
from src.core.config import logger
from src.db.repositories.quotations import QuotationRepo
from src.db.repositories.products import ProductRepo
from src.services.pdf_generator import generate_quotation_pdf
from src.channels.wa_webjs import WAWebJSProvider

ORG_ID = "00000000-0000-0000-0000-000000000001"


def generate_quotation(job: dict) -> None:
    payload = job.get("payload", {})
    lead_id = payload.get("lead_id")
    contact_id = payload.get("contact_id")
    items = payload.get("items", [])
    channel_id = payload.get("channel_id")
    from_number = payload.get("from_number")

    if not lead_id:
        logger.warning("generate_quotation: no lead_id, skipping")
        return

    q_repo = QuotationRepo()
    p_repo = ProductRepo()

    subtotal = 0.0
    quotation_items = []
    for item in items:
        name = item.get("name", "")
        qty = item.get("qty", 1)
        products = p_repo.list_by_org(ORG_ID)
        product = next((p for p in products if p["name"].lower() == name.lower()), None)
        unit_price = product["unit_price"] if product else 0.0
        line_total = unit_price * qty
        subtotal += line_total
        quotation_items.append({
            "description": name,
            "qty": qty,
            "unit_price": unit_price,
            "line_total": line_total,
            "product_id": product["id"] if product else None,
        })

    tax = round(subtotal * 0.06, 2)
    total = round(subtotal + tax, 2)

    from src.db.repositories.jobs import JobRepo
    j_repo = JobRepo()

    import uuid
    lead_id_uuid = uuid.UUID(lead_id) if isinstance(lead_id, str) else lead_id
    quotation = q_repo.create(
        org_id=ORG_ID,
        lead_id=str(lead_id_uuid),
        number=f"Q-DEFAULT-{uuid.uuid4().hex[:8].upper()}",
        subtotal=subtotal,
        tax=tax,
        total=total,
    )

    for qi in quotation_items:
        q_repo.add_item(
            quotation_id=quotation["id"],
            description=qi["description"],
            qty=qi["qty"],
            unit_price=qi["unit_price"],
            line_total=qi["line_total"],
            product_id=qi.get("product_id"),
        )

    pdf_path = generate_quotation_pdf(quotation, quotation_items)
    logger.info(f"Quotation PDF generated: {pdf_path}")

    if pdf_path and channel_id:
        channel = WAWebJSProvider()
        public_url = f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:7860')}/quotations/{os.path.basename(pdf_path)}"
        channel.send_document(
            channel_id, from_number, public_url,
            caption=f"Quotation {quotation['number']} - RM{total:.2f}",
        )
