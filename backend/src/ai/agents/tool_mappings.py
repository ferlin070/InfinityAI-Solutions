"""Per-agent tool registry. Maps each agent key to its CrewAI tools.

Three sources of tools, merged per agent:

1. **Static** — first-party tools in `src/ai/tools/*` (DB lookups, workflow
   triggers, domain queries). Curated per agent based on their role —
   adding a tool here is the single change needed to extend an agent.

2. **Browser** — Playwright-based tools in `src/ai/browser/tools.py`.
   Only attached to agents that need to drive a browser (Hakim for system
   inspection, Danish/Aiman for web research, Amelia for content
   research). Loaded only if Playwright is installed; otherwise silently
   skipped. Subset is controlled by `BROWSER_TOOL_AGENTS` /
   `BROWSER_TOOL_NAMES` below — not every agent gets every browser tool.

3. **MCP** — external MCP server tools, loaded once at startup and
   attached globally to every agent (they are agent-agnostic capabilities
   the AI can opt into). See `src/ai/mcp/MCPRegistry`.

`STATIC_TOOL_MAPPINGS` is the per-agent static list — `get_tools()` in this
file is the single source of truth that `build_crewai_agent()` reads and
wires into `crewai.Agent(tools=...)`. For image-capable agents, the image
tool is appended on top when a run supplies an `artifact_collector`.
"""

import logging
from functools import lru_cache

from src.ai.tools import (
    # Original domain tools
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
from src.ai.tools.image_generation import build_image_generation_tool

logger = logging.getLogger("ai_command_center")


# Agents that get an image-generation tool when a run supplies an artifact
# collector (see backend/src/ai/tools/image_generation.py). Danish only —
# he's InfinityAI's Kreatif specialist (banners, posters, visual content).
IMAGE_CAPABLE_AGENTS = {"DANISH"}


# Agents that get any browser tools at all. Each gets a *subset* (see
# `_BROWSER_TOOL_NAMES_BY_AGENT`); Hakim gets the full set since his job
# is to drive the platform UI to verify behaviour.
_BROWSER_TOOL_AGENTS = {"HAKIM", "DANISH", "AIMAN", "AMELIA"}


# Per-agent browser-tool subset. Agents not listed here get no browser tools.
# "all" is shorthand for "every loaded browser tool" (used by Hakim).
_BROWSER_TOOL_NAMES_BY_AGENT: dict[str, set[str] | str] = {
    "HAKIM": "all",
    "DANISH": {"Browser Navigate", "Browser Extract Text", "Browser Get UI State", "Browser Screenshot"},
    "AIMAN": {"Browser Navigate", "Browser Extract Text", "Browser Screenshot"},
    "AMELIA": {"Browser Navigate", "Browser Extract Text"},
}


# Per-agent static tool lists (curated by role, no browser tools here — those
# are layered in by `get_tools()` based on `_BROWSER_TOOL_NAMES_BY_AGENT`).
# Adding a tool here is a one-line edit; `get_tools()` wires it up.
STATIC_TOOL_MAPPINGS: dict[str, list] = {
    # Claudia: Chief of Staff, routes only — no execution tools.
    "CLAUDIA": [],

    # Maya: Sales & CRM. Pricing, contact lookup, conversation history,
    # lead/contact upserts, and the end-to-end quotation workflow.
    "MAYA": [
        product_pricing_tool,
        contact_info_tool,
        conversation_history_tool,
        db_search_products_tool,
        db_upsert_contact_tool,
        db_upsert_lead_tool,
        workflow_generate_quotation_tool,
    ],

    # Hakim: System Architect + IT. System docs + generic DB reads.
    # Browser tools added by get_tools() (full set).
    "HAKIM": [
        system_documentation_tool,
        db_list_products_tool,
        db_list_channels_tool,
    ],

    # Zara: Finance. Reads products (for invoicing) and the pending
    # approval queue; can approve quotations.
    "ZARA": [
        db_list_products_tool,
        db_list_pending_quotations_tool,
        db_approve_quotation_tool,
    ],

    # Danish: Content / creative. Product lookups for accurate copy.
    # Image-generation tool added dynamically when a run supplies an
    # artifact_collector; browser-research subset added by get_tools().
    "DANISH": [
        db_list_products_tool,
        db_search_products_tool,
    ],

    # Aiman: Marketing. Pipeline/audience data.
    # Browser research subset added by get_tools().
    "AIMAN": [
        db_list_leads_tool,
        db_list_contacts_tool,
    ],

    # Amelia: Training. (Browser research subset added by get_tools().)
    "AMELIA": [],

    # Adila: Operations. Pipeline summary, briefing trigger, generic job
    # scheduler, and conversation/lead reads for ops triage.
    "ADILA": [
        workflow_lead_pipeline_summary_tool,
        workflow_trigger_daily_briefing_tool,
        workflow_schedule_job_tool,
        db_list_open_conversations_tool,
        db_list_leads_tool,
    ],
}


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


def _browser_tools_for(agent_key: str) -> list:
    """Browser tools filtered to the subset this agent is allowed to use."""
    if agent_key not in _BROWSER_TOOL_AGENTS:
        return []
    subset = _BROWSER_TOOL_NAMES_BY_AGENT.get(agent_key)
    if subset == "all":
        return list(_browser_tools())
    if not subset:
        return []
    return [t for t in _browser_tools() if t.name in subset]


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


def get_tools(agent_key: str, artifact_collector: list[dict] | None = None) -> list:
    """Resolve the full tool list for an agent:

    1. Static tools from `STATIC_TOOL_MAPPINGS` (curated per role).
    2. Browser tools filtered to the agent's allowed subset.
    3. Image-generation tool (image-capable agents only, only when an
       `artifact_collector` is supplied — no collector, no tool, since
       there'd be nowhere for the generated image to go).
    4. MCP tools loaded once from `MCP_SERVERS` (agent-agnostic; layered
       on every agent).

    Adding/removing a static tool is a one-line edit in `STATIC_TOOL_MAPPINGS`.
    Adjusting browser access is a one-line edit in
    `_BROWSER_TOOL_NAMES_BY_AGENT`. No call-site changes anywhere else.
    """
    key = agent_key.upper()
    tools = list(STATIC_TOOL_MAPPINGS.get(key, []))
    tools.extend(_browser_tools_for(key))
    if key in IMAGE_CAPABLE_AGENTS and artifact_collector is not None:
        tools.append(build_image_generation_tool(artifact_collector))
    tools.extend(_mcp_tools())
    return tools
