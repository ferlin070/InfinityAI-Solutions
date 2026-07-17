from crewai.tools import tool
from src.db.repositories.messages import MessageRepo
from src.db.repositories.conversations import ConversationRepo

ORG_ID = "00000000-0000-0000-0000-000000000001"


@tool("Conversation History")
def conversation_history_tool(contact_phone: str) -> str:
    """Get recent conversation history for a contact by phone number.
    Returns the last 20 messages in chronological order."""
    try:
        conv_repo = ConversationRepo()
        msg_repo = MessageRepo()

        conv = conv_repo.get_open_by_contact(ORG_ID, contact_phone)
        if not conv:
            return "No active conversation found for this contact."

        msgs = msg_repo.list_by_conversation(ORG_ID, conv["id"], limit=20)
        if not msgs:
            return "No messages in this conversation."

        history = []
        for m in msgs:
            sender = m.get("sender", "unknown")
            body = m.get("body", "")
            time = m.get("created_at", "")[:16]
            history.append(f"[{time}] {sender}: {body}")
        return "\n".join(history)
    except Exception as e:
        return f"Error fetching conversation: {e}"
