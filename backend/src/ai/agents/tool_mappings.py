"""Per-agent tool registry. Maps each agent key to its CrewAI tools.

Three sources of tools, merged per agent:

1. **Static** — first-party tools in `src/ai/tools/*` (DB lookups, workflow
   triggers, domain queries). Curated per agent based on their role —
   adding a tool here is the single change needed to extend an agent.

2. **Browser** — Playwright-based tools in `src/ai/browser/tools.py`.
   Only attached to agents that need to drive a browser (Hakim for system
   inspection, Danish/Aiman for web research, Amelia for content
   research, and NEXUS as the generalist fallback). Loaded only if
   Playwright is installed; otherwise silently skipped. Subset is
   controlled by `_BROWSER_TOOL_AGENTS` / `_BROWSER_TOOL_NAMES_BY_AGENT`
   below — not every agent gets every browser tool.

3. **MCP** — external MCP server tools, loaded once at startup and
   attached globally to every agent (they are agent-agnostic capabilities
   the AI can opt into). See `src/ai/mcp/MCPRegistry`.

`STATIC_TOOL_MAPPINGS` is the per-agent static list — `get_tools()` in this
file is the single source of truth that `build_crewai_agent()` reads and
wires into `crewai.Agent(tools=...)`. For image-capable agents, the image
tool is appended on top when a run supplies an `artifact_collector`.

NEXUS is the generalist fallback: `get_tools("NEXUS")` returns the union
of every static tool (deduplicated), the full browser set, MCP, and image
generation when an artifact_collector is supplied. Claudia routes to
NEXUS for multi-domain, vague, or capability-mismatch requests.
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
    # Business profile tools
    db_get_business_profile_tool,
    db_update_business_profile_tool,
    # Platform self-discovery tools (work in live + demo mode)
    db_discover_platform_tool,
    db_get_configuration_status_tool,
    db_get_recent_activity_tool,
    db_platform_status_tool,
    # Tool registry discovery (agentic-v3)
    discover_tools_tool,
    # Workflow tools
    workflow_trigger_inbound_reply_tool,
    workflow_generate_quotation_tool,
    workflow_trigger_daily_briefing_tool,
    workflow_lead_pipeline_summary_tool,
    workflow_schedule_job_tool,
)
from src.ai.tools.image_generation import build_image_generation_tool
from src.ai.agentic.registry import ToolRegistry, register as _register_tool

logger = logging.getLogger("ai_command_center")


# ─── ToolRegistry: index every tool with metadata (capabilities, owners,
# approval, risk). The Registry is queried at runtime by
# `discover_tools_tool` and (in Phase 2) used for policy enforcement.
# Adding a new tool = one `_register_tool(...)` call here. Idempotent.
_register_tool(
    "Product Pricing", "Semak harga produk dalam katalog.",
    capabilities=["product.read", "pricing.read"], owner_agents=("MAYA", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "Contact Info", "Cari profil contact + lead ikut nombor telefon.",
    capabilities=["crm.read", "contact.read", "lead.read"], owner_agents=("MAYA", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "Conversation History", "Sejarah perbualan WhatsApp untuk contact.",
    capabilities=["crm.read", "conversation.read"], owner_agents=("MAYA", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "System Documentation", "Cari maklumat tepat dari dokumentasi sistem.",
    capabilities=["docs.read", "system.read"], owner_agents=("HAKIM",),
    risk_level="low",
)
_register_tool(
    "DB List Contacts", "Senaraikan contact dalam CRM, paling baru dulu.",
    capabilities=["crm.read", "contact.list"], owner_agents=("MAYA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Upsert Contact", "Cipta atau kemas kini contact ikut nombor telefon.",
    capabilities=["crm.write", "contact.write"], owner_agents=("MAYA", "NEXUS"),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB Update Contact Tags", "Ganti senarai tag pada contact.",
    capabilities=["crm.write", "contact.write"], owner_agents=("MAYA", "NEXUS"),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB List Leads", "Senaraikan leads, dengan filter ikut skor (hot/warm/cold).",
    capabilities=["crm.read", "lead.list"], owner_agents=("MAYA", "AIMAN", "ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Upsert Lead", "Cipta atau kemas kini lead untuk contact.",
    capabilities=["crm.write", "lead.write"], owner_agents=("MAYA", "NEXUS"),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB List Products", "Senarai katalog produk dengan harga + stok.",
    capabilities=["product.read"], owner_agents=("MAYA", "ZARA", "DANISH", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Search Products", "Cari produk ikut teks (nama / description).",
    capabilities=["product.read", "product.search"], owner_agents=("MAYA", "DANISH", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Create Product", "Tambah produk baru dalam katalog.",
    capabilities=["product.write"], owner_agents=("NEXUS",),
    risk_level="medium", live_only=True,
    requires_approval=True,
)
_register_tool(
    "DB Create Quotation", "Cipta sebut harga (status pending_approval).",
    capabilities=["quotation.write", "crm.write"], owner_agents=("MAYA", "NEXUS"),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB Approve Quotation", "Luluskan sebut harga (pending_approval -> sent).",
    capabilities=["quotation.write", "finance.write"], owner_agents=("ZARA", "NEXUS"),
    risk_level="high", live_only=True,
    requires_approval=True,
)
_register_tool(
    "DB List Pending Quotations", "Senarai sebut harga menunggu kelulusan.",
    capabilities=["quotation.read"], owner_agents=("ZARA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Enqueue Job", "Letak kerja dalam queue async.",
    capabilities=["jobs.write"], owner_agents=("ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB List Open Conversations", "Senarai perbualan terbuka + contact.",
    capabilities=["conversation.read"], owner_agents=("ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Create Conversation", "Buka perbualan baru untuk contact.",
    capabilities=["conversation.write"], owner_agents=("NEXUS",),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB Save Message", "Simpan mesej dalam perbualan.",
    capabilities=["conversation.write"], owner_agents=("NEXUS",),
    risk_level="medium", live_only=True,
)
_register_tool(
    "DB List Channels", "Senarai WhatsApp channel + status.",
    capabilities=["whatsapp.read", "channel.list"], owner_agents=("HAKIM", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Get Business Profile", "Baca profil perniagaan syarikat.",
    capabilities=["profile.read"], owner_agents=("CLAUDIA", "ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "DB Update Business Profile", "Kemas kini profil perniagaan.",
    capabilities=["profile.write"], owner_agents=("ADILA", "NEXUS"),
    risk_level="high", live_only=True,
    requires_approval=True,
)
_register_tool(
    "DB Discover Platform", "Katalog halaman + API platform.",
    capabilities=["platform.discover"], owner_agents=("CLAUDIA", "HAKIM", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "DB Platform Status", "Status platform aggregate (WhatsApp, leads, dll).",
    capabilities=["platform.status"], owner_agents=("CLAUDIA", "HAKIM", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "DB Get Configuration Status", "Apa yang sudah/belum disetup (DB, providers, dll).",
    capabilities=["config.read", "system.diagnose"], owner_agents=("CLAUDIA", "HAKIM", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "DB Get Recent Activity", "Aktiviti terkini dari daily_log.json.",
    capabilities=["activity.read"], owner_agents=("CLAUDIA", "HAKIM", "NEXUS"),
    risk_level="low",
)
_register_tool(
    "DB Discover Tools", "Discover tool yang tersedia ikut capability/owner/query.",
    capabilities=["meta.discover", "tool.discover"], owner_agents=("HAKIM", "NEXUS"),
    risk_level="low",
)
# Workflow / business-process tools
_register_tool(
    "Workflow Trigger Inbound Reply", "End-to-end inbound WhatsApp flow.",
    capabilities=["workflow.inbound", "crm.write"], owner_agents=("NEXUS",),
    risk_level="medium", live_only=True,
)
_register_tool(
    "Workflow Generate Quotation", "End-to-end jana sebut harga.",
    capabilities=["workflow.quotation", "crm.write"], owner_agents=("MAYA", "NEXUS"),
    risk_level="medium", live_only=True,
)
_register_tool(
    "Workflow Trigger Daily Briefing", "Enqueue daily briefing job.",
    capabilities=["workflow.briefing", "jobs.write"], owner_agents=("ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "Workflow Lead Pipeline Summary", "Ringkasan pipeline leads (count + top hot).",
    capabilities=["crm.read", "lead.summary"], owner_agents=("ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
_register_tool(
    "Workflow Schedule Job", "Schedule generic job.",
    capabilities=["jobs.write"], owner_agents=("ADILA", "NEXUS"),
    risk_level="low", live_only=True,
)
# Image generation (Danish + NEXUS)
_register_tool(
    "Image Generation", "Jana imej sebenar (banner, poster, grafik) dengan DALL-E.",
    capabilities=["image.generate"], owner_agents=("DANISH", "NEXUS"),
    risk_level="medium",
)
# Browser tools (HAKIM + NEXUS full; others subset)
for _name in (
    "Browser Navigate", "Browser Click", "Browser Type",
    "Browser Select Dropdown", "Browser Screenshot", "Browser Get UI State",
    "Browser Scroll", "Browser Wait For", "Browser Extract Text",
    "Browser Close Session",
):
    _register_tool(
        _name, f"Playwright/Chromium tool: {_name.split(maxsplit=1)[-1].lower()}.",
        capabilities=["browser", "browser.automation"],
        owner_agents=("HAKIM", "NEXUS"),
        risk_level="medium",
    )

logger.info(f"ToolRegistry: {len(ToolRegistry.get().all())} tools registered.")


# Agents that get an image-generation tool when a run supplies an artifact
# collector (see backend/src/ai/tools/image_generation.py). Danish and NEXUS
# (NEXUS gets it because it's the generalist).
IMAGE_CAPABLE_AGENTS = {"DANISH", "NEXUS"}


# Agents that get any browser tools at all. Each gets a *subset* (see
# `_BROWSER_TOOL_NAMES_BY_AGENT`); Hakim and NEXUS get the full set.
_BROWSER_TOOL_AGENTS = {"HAKIM", "DANISH", "AIMAN", "AMELIA", "NEXUS"}


# Per-agent browser-tool subset. Agents not listed here get no browser tools.
# "all" is shorthand for "every loaded browser tool" (used by Hakim + NEXUS).
_BROWSER_TOOL_NAMES_BY_AGENT: dict[str, set[str] | str] = {
    "HAKIM": "all",
    "NEXUS": "all",
    "DANISH": {"Browser Navigate", "Browser Extract Text", "Browser Get UI State", "Browser Screenshot"},
    "AIMAN": {"Browser Navigate", "Browser Extract Text", "Browser Screenshot"},
    "AMELIA": {"Browser Navigate", "Browser Extract Text"},
}


# Per-agent static tool lists (curated by role, no browser tools here — those
# are layered in by `get_tools()` based on `_BROWSER_TOOL_NAMES_BY_AGENT`).
# Adding a tool here is a one-line edit; `get_tools()` wires it up.
STATIC_TOOL_MAPPINGS: dict[str, list] = {
    # Claudia: Chief of Staff + Chief of Inquiry. Has a small "quick-check"
    # toolset so she can answer the user's status / config / discovery
    # questions DIRECTLY (with a real tool call) instead of just chatting.
    # Deeper work still routes to a specialist via `accepted` — see
    # `prompts/loader.py` for the routing rules.
    "CLAUDIA": [
        db_platform_status_tool,
        db_get_configuration_status_tool,
        db_discover_platform_tool,
        db_get_recent_activity_tool,
        db_get_business_profile_tool,
    ],

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

    # Hakim: System Architect + IT. System docs + platform self-discovery
    # (so he can answer "where do I find X?"), DB reads, the full
    # browser toolset (added by get_tools()), AND the meta discover-tools
    # tool (so he can answer "which tool does X?").
    "HAKIM": [
        system_documentation_tool,
        discover_tools_tool,
        db_discover_platform_tool,
        db_platform_status_tool,
        db_get_configuration_status_tool,
        db_get_recent_activity_tool,
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
    # scheduler, conversation/lead reads, AND business profile
    # read/write (sole owner of the business profile tools).
    "ADILA": [
        workflow_lead_pipeline_summary_tool,
        workflow_trigger_daily_briefing_tool,
        workflow_schedule_job_tool,
        db_list_open_conversations_tool,
        db_list_leads_tool,
        db_get_business_profile_tool,
        db_update_business_profile_tool,
    ],

    # NEXUS: Generalist fallback. Starts empty — `get_tools("NEXUS")` builds
    # the union of every static tool (deduplicated), plus full browser
    # set, MCP, and image-gen (when collector supplied). Keep this list
    # empty unless you want NEXUS to have a non-union tool that no other
    # agent has.
    "NEXUS": [],
}


# NEXUS sees the union of every static tool across all agents (plus its
# own). Computed once at module load.
def _all_static_tools() -> list:
    """Union (deduplicated, order-preserving) of every tool in
    STATIC_TOOL_MAPPINGS except NEXUS's own list (which is empty by
    convention but included for safety)."""
    seen: set = set()
    union: list = []
    for agent_key, tools in STATIC_TOOL_MAPPINGS.items():
        if agent_key == "NEXUS":
            continue
        for t in tools:
            if id(t) in seen:
                continue
            seen.add(id(t))
            union.append(t)
    return union


# Per-agent static tool list returned for NEXUS — see `get_tools()`.
_NEXUS_STATIC_TOOLS: list = _all_static_tools()


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
       NEXUS gets the union of every other agent's static list.
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
    if key == "NEXUS":
        tools = list(_NEXUS_STATIC_TOOLS)
    else:
        tools = list(STATIC_TOOL_MAPPINGS.get(key, []))
    tools.extend(_browser_tools_for(key))
    if key in IMAGE_CAPABLE_AGENTS and artifact_collector is not None:
        tools.append(build_image_generation_tool(artifact_collector))
    tools.extend(_mcp_tools())
    return tools
