"""Central registry mapping agent keys to their CrewAI tools.

Every agent gets its tools automatically via `build_crewai_agent()` in
`factory.py` — adding a new static tool for an agent is a one-line change
here, zero changes to flows or factory call-sites.
"""

from src.ai.tools import (
    contact_info_tool,
    conversation_history_tool,
    product_pricing_tool,
    system_documentation_tool,
)
from src.ai.tools.image_generation import build_image_generation_tool

STATIC_TOOL_MAPPINGS: dict[str, list] = {
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

# Agents that get an image-generation tool when a run supplies an artifact
# collector (see backend/src/ai/tools/image_generation.py). Danish only —
# he's InfinityAI's Kreatif specialist (banners, posters, visual content).
IMAGE_CAPABLE_AGENTS = {"DANISH"}


def get_tools(agent_key: str, artifact_collector: list[dict] | None = None) -> list:
    """Resolve the full tool list for an agent: static tools plus, for
    image-capable agents, an image-generation tool bound to this run's
    `artifact_collector` (only when one is supplied — no collector, no tool,
    since there'd be nowhere for the generated image to go)."""
    tools = list(STATIC_TOOL_MAPPINGS.get(agent_key, []))
    if agent_key in IMAGE_CAPABLE_AGENTS and artifact_collector is not None:
        tools.append(build_image_generation_tool(artifact_collector))
    return tools
