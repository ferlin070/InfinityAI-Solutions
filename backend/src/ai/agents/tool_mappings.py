"""Per-agent tool registry. Maps each agent key to its CrewAI tools.

Three sources of tools, merged per agent:

1. **Static** — first-party tools in `src/ai/tools/*` (DB lookups, workflow
   triggers, domain queries). Curated per agent based on their role —
   adding a tool here is the single change needed to extend an agent.

2. **Browser** — Playwright-based tools in `src/ai/browser/tools.py`.
   Only attached to agents that need to drive a browser (Hakim for system
   inspection, Danish/Aiman for web research, Amelia for content
   research). Loaded only if Playwright is installed; otherwise silently
   skipped.

3. **MCP** — external MCP server tools, loaded once at startup and
   attached globally to every agent (they are agent-agnostic capabilities
   the AI can opt into). See `src/ai/mcp/MCPRegistry`.

`TOOL_MAPPINGS` is the single source of truth — `build_crewai_agent()`
in `factory.py` reads it and wires the result into `crewai.Agent(tools=...)`.
"""

import logging
from functools import lru_cache

from src.ai.tools import (
    # Original tools
    product_pricing_tool,
    contact_info_tool,
    conversation_history_tool,
    system_documentation_tool,
    # Database tools
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
    # Workflow tools
    workflow_trigger_inbound_reply_tool,
    workflow_generate_quotation_tool,
    workflow_trigger_daily_briefing_tool,
    workflow_lead_pipeline_summary_tool,
    workflow_schedule_job_tool,
)

logger = logging.getLogger("ai_command_center")


@lru_cache(maxsize=1)
def _browser_tools() -> list:
    """Return Playwright browser tools. Returns [] if Playwright is not
    installed (so the system keeps running without the optional dep)."""
    try:
        from src.ai.browser.tools import (  # type: ignore
            browser_navigate_tool,
            browser_click_tool,
            browser_type_tool,
            browser_select_tool,
            browser_screenshot_tool,
            browser_get_ui_state_tool,
            browser_scroll_tool,
            browser_wait_for_tool,
            browser_extract_text_tool,
            browser_close_session_tool,
        )
    except Exception as e:
        logger.info(f"Browser tools disabled (Playwright not available): {e}")
        return []
    return [
        browser_navigate_tool,
        browser_click_tool,
        browser_type_tool,
        browser_select_tool,
        browser_screenshot_tool,
        browser_get_ui_state_tool,
        browser_scroll_tool,
        browser_wait_for_tool,
        browser_extract_text_tool,
        browser_close_session_tool,
    ]


@lru_cache(maxsize=1)
def _mcp_tools() -> list:
    """Return MCP-exposed tools from all configured servers. Returns [] if
    MCP SDK is not installed or no servers are configured."""
    try:
        from src.ai.mcp import MCPRegistry  # type: ignore
    except Exception as e:
        logger.info(f"MCP tools disabled: {e}")
        return []
    try:
        defs = MCPRegistry.load_tools()
        return MCPRegistry.to_crewai_tools(defs)
    except Exception as e:
        logger.warning(f"Failed to load MCP tools: {e}")
        return []


# Per-agent tool lists. Curated by role — keep tight, LLM context is expensive.
TOOL_MAPPINGS: dict[str, list] = {
    # Claudia: Chief of Staff, routes only — no execution tools.
    "CLAUDIA": [],

    # Maya: Sales & CRM. Needs to look up products, contacts, history, then
    # upsert leads/contacts and create quotations.
    "MAYA": [
        product_pricing_tool,
        contact_info_tool,
        conversation_history_tool,
        db_search_products_tool,
        db_upsert_contact_tool,
        db_upsert_lead_tool,
        workflow_generate_quotation_tool,
    ],

    # Hakim: System Architect + IT. The system-docs tool plus the browser
    # tools (so he can drive the platform UI to verify behaviour) plus
    # generic DB read tools for sanity checks.
    "HAKIM": [
        system_documentation_tool,
        db_list_products_tool,
        db_list_channels_tool,
        *_browser_tools(),
    ],

    # Zara: Finance. Reads products (for invoicing) and the pending
    # approval queue; can approve quotations.
    "ZARA": [
        db_list_products_tool,
        db_list_pending_quotations_tool,
        db_approve_quotation_tool,
    ],

    # Danish: Content / creative. Browser-driven research (pull references
    # from the web) plus product lookups for accurate copy.
    "DANISH": [
        db_list_products_tool,
        db_search_products_tool,
        *[_t for _t in _browser_tools() if _t.name in (
            "Browser Navigate",
            "Browser Extract Text",
            "Browser Get UI State",
            "Browser Screenshot",
        )],
    ],

    # Aiman: Marketing. Pipeline/audience data + browser for competitor
    # research and landing-page checks.
    "AIMAN": [
        db_list_leads_tool,
        db_list_contacts_tool,
        *[_t for _t in _browser_tools() if _t.name in (
            "Browser Navigate",
            "Browser Extract Text",
            "Browser Screenshot",
        )],
    ],

    # Amelia: Training. Research materials from the web.
    "AMELIA": [
        *[_t for _t in _browser_tools() if _t.name in (
            "Browser Navigate",
            "Browser Extract Text",
        )],
    ],

    # Adila: Operations. Daily-briefing, lead pipeline, and the
    # generic job scheduler for ad-hoc ops tasks.
    "ADILA": [
        workflow_lead_pipeline_summary_tool,
        workflow_trigger_daily_briefing_tool,
        workflow_schedule_job_tool,
        db_list_open_conversations_tool,
        db_list_leads_tool,
    ],
}


def get_tools_for_agent(agent_key: str) -> list:
    """Return the static + browser tool list for an agent. MCP tools are
    layered on top by `get_all_tools_for_agent`."""
    return list(TOOL_MAPPINGS.get(agent_key.upper(), []))


def get_all_tools_for_agent(agent_key: str) -> list:
    """Return every tool an agent can call: static + browser + MCP."""
    return get_tools_for_agent(agent_key) + _mcp_tools()
