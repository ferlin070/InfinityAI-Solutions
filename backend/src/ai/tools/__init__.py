"""Agent-callable tools (function-calling). Each module here defines one or
more `@tool("Name")` decorated functions; this `__init__` re-exports them so
callers can do `from src.ai.tools import product_pricing_tool` and the rest of
the system can register them via `TOOL_MAPPINGS` in
`src/ai/agents/tool_mappings.py`.

Two flavours of tools live here:
- Domain tools (read/write on existing repos) — `db_tools.py`, `workflow_tools.py`.
- Documentation/system tools — `system_docs.py`, `product_pricing.py`, etc.

Browser tools live in `src/ai/browser/tools.py` and are re-exported there.
MCP tools are loaded dynamically via `src/ai/mcp/MCPRegistry`.
"""

from .product_pricing import product_pricing_tool
from .contact_info import contact_info_tool
from .conversation_history import conversation_history_tool
from .system_docs import system_documentation_tool
from .db_tools import (
    db_list_contacts_tool,
    db_upsert_contact_tool,
    db_update_contact_tags_tool,
    db_list_leads_tool,
    db_upsert_lead_tool,
    db_list_products_tool,
    db_search_products_tool,
    db_create_product_tool,
    db_create_quotation_tool,
    db_approve_quotation_tool,
    db_list_pending_quotations_tool,
    db_enqueue_job_tool,
    db_list_open_conversations_tool,
    db_create_conversation_tool,
    db_save_message_tool,
    db_list_channels_tool,
)
from .workflow_tools import (
    workflow_trigger_inbound_reply_tool,
    workflow_generate_quotation_tool,
    workflow_trigger_daily_briefing_tool,
    workflow_lead_pipeline_summary_tool,
    workflow_schedule_job_tool,
)

__all__ = [
    # Original tools
    "product_pricing_tool",
    "contact_info_tool",
    "conversation_history_tool",
    "system_documentation_tool",
    # Database tools
    "db_list_contacts_tool",
    "db_upsert_contact_tool",
    "db_update_contact_tags_tool",
    "db_list_leads_tool",
    "db_upsert_lead_tool",
    "db_list_products_tool",
    "db_search_products_tool",
    "db_create_product_tool",
    "db_create_quotation_tool",
    "db_approve_quotation_tool",
    "db_list_pending_quotations_tool",
    "db_enqueue_job_tool",
    "db_list_open_conversations_tool",
    "db_create_conversation_tool",
    "db_save_message_tool",
    "db_list_channels_tool",
    # Workflow tools
    "workflow_trigger_inbound_reply_tool",
    "workflow_generate_quotation_tool",
    "workflow_trigger_daily_briefing_tool",
    "workflow_lead_pipeline_summary_tool",
    "workflow_schedule_job_tool",
]
