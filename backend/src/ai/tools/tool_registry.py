"""`DB Discover Tools` — agent-facing tool that queries the
ToolRegistry at runtime so the LLM can discover what tools exist
without having every tool's docstring in its prompt.

This is a "meta tool" — its only job is to list other tools.

In Phase 1 the registry is populated when `register_all_tools()` is
called (imported from `tool_mappings.py`). Phase 2 will make the
registry the single source of truth, replacing `STATIC_TOOL_MAPPINGS`.
"""

import json
from typing import Optional

from crewai.tools import tool

from src.ai.agentic.registry import ToolRegistry
from src.core.config import logger


def _entry_to_dict(e) -> dict:
    return {
        "name": e.name,
        "description": e.description,
        "capabilities": list(e.capabilities),
        "owner_agents": list(e.owner_agents),
        "requires_approval": e.requires_approval,
        "risk_level": e.risk_level,
        "live_only": e.live_only,
    }


@tool("DB Discover Tools")
def discover_tools_tool(
    query: Optional[str] = None,
    capability: Optional[str] = None,
    owner_agent: Optional[str] = None,
) -> str:
    """Senaraikan tool yang tersedia dalam sistem, dengan penerangan
    ringkas, kebolehan (capability), dan ejen pemilik. Guna untuk
    discover tool yang sesuai pada runtime — jangan assume tool apa
    yang ada.

    Penapis (semua optional, boleh digabung):
    - `query` — carian teks bebas (substring nama / description / capability)
    - `capability` — tapis ikut capability tag (contoh: 'crm.read', 'browser', 'image.generate')
    - `owner_agent` — tapis ikut ejen pemilik (contoh: 'HAKIM', 'NEXUS')

    Contoh:
    - discover_tools_tool() — semua tool
    - discover_tools_tool(query='lead') — cari tool berkaitan lead
    - discover_tools_tool(capability='crm.read') — semua tool yang boleh baca CRM
    - discover_tools_tool(owner_agent='HAKIM') — semua tool yang HAKIM ada"""
    try:
        reg = ToolRegistry.get()
        # Capability filter first (most selective), then owner, then text.
        if capability:
            entries = reg.list_by_capability(capability)
        elif owner_agent:
            entries = [e for e in reg.all() if owner_agent in e.owner_agents]
        elif query:
            entries = reg.find(query)
        else:
            entries = reg.all()

        result = [_entry_to_dict(e) for e in entries]
        if not result:
            return (
                f"Tiada tool匹配 untuk query={query!r}, "
                f"capability={capability!r}, owner_agent={owner_agent!r}. "
                f"Cuba tanpa filter untuk lihat semua tool yang tersedia."
            )
        # Group by capability for readability
        by_cap: dict[str, list[dict]] = {}
        for r in result:
            for cap in r["capabilities"]:
                by_cap.setdefault(cap, []).append({"name": r["name"], "description": r["description"]})

        return json.dumps({
            "count": len(result),
            "tools": result,
            "grouped_by_capability": by_cap,
            "tip": (
                "Untuk data, panggil tool yang sesuai dengan namanya. "
                "Untuk tool destructive (requires_approval=true), Coordinator "
                "akan minta kelulusan manusia dulu."
            ),
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"discover_tools_tool failed: {e}")
        return f"Error listing tools: {e}"
