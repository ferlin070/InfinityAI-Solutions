from crewai.tools import tool
from src.db.repositories.contacts import ContactRepo
from src.db.repositories.leads import LeadRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


@tool("Contact Info")
def contact_info_tool(phone_number: str) -> str:
    """Look up contact and lead information by phone number.
    Returns name, source, tags, lead score, and interest summary."""
    try:
        contact_repo = ContactRepo()
        lead_repo = LeadRepo()

        contact = contact_repo.get_by_phone(ORG_ID, phone_number)
        if not contact:
            return f"No contact found for phone: {phone_number}"

        info = f"Name: {contact.get('name', 'Unknown')}\n"
        info += f"Phone: {contact['phone']}\n"
        info += f"Source: {contact.get('source', 'N/A')}\n"
        if contact.get("tags"):
            info += f"Tags: {', '.join(contact['tags'])}\n"

        lead = lead_repo.get_by_contact(ORG_ID, contact["id"])
        if lead:
            info += f"Lead Score: {lead.get('score', 'cold')}\n"
            info += f"Lead Status: {lead.get('status', 'new')}\n"
            if lead.get("interest_summary"):
                info += f"Interest: {lead['interest_summary']}\n"
            if lead.get("score_reason"):
                info += f"Score Reason: {lead['score_reason']}\n"

        return info
    except Exception as e:
        return f"Error looking up contact: {e}"
