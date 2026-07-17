"""Central registry mapping agent keys to their CrewAI tools.

Every agent gets its tools automatically via `build_crewai_agent()` in
`factory.py` — adding a new tool for an agent is a one-line change here,
zero changes to flows or factory call-sites.
"""

from src.ai.tools import (
    contact_info_tool,
    conversation_history_tool,
    product_pricing_tool,
    system_documentation_tool,
)

TOOL_MAPPINGS: dict[str, list] = {
    "MAYA": [
        product_pricing_tool,
        contact_info_tool,
        conversation_history_tool,
    ],
    "HAKIM": [
        system_documentation_tool,
    ],
    "CLAUDIA": [],
    "ZARA": [],
    "AMELIA": [],
    "DANISH": [],
    "AIMAN": [],
    "ADILA": [],
}
