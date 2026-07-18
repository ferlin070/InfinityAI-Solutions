"""Tool Registry — queryable catalog of every tool the agentic system
exposes, with capabilities, owners, and approval flags.

Why this exists:
- The current `STATIC_TOOL_MAPPINGS` says "agent X has tools Y, Z" but
  doesn't say what each tool DOES or what capability it offers. The LLM
  has to read every tool's docstring to find the right one.
- Phase 1 of agentic-v3 introduces dynamic tool discovery: an agent
  asks "which tools can read leads?" and gets a filtered list back,
  with a one-line description each. Less prompt bloat, better selection.
- Phase 3 will add approval flags: a `requires_approval=True` tool
  gates execution behind a human checkpoint.

This is a passive catalog — registering a tool here doesn't auto-attach
it to any agent. `STATIC_TOOL_MAPPINGS` in `tool_mappings.py` is still
the source of truth for "who gets what". The registry is a parallel
index used for discovery and policy decisions.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.core.config import logger


@dataclass(frozen=True)
class ToolEntry:
    """One tool in the registry."""
    name: str
    description: str
    capabilities: tuple[str, ...]                # e.g. ("crm.read", "lead.read")
    owner_agents: tuple[str, ...] = ()           # which agents typically own it
    requires_approval: bool = False               # destructive ops gate behind human approval
    risk_level: str = "low"                       # "low" | "medium" | "high" — UI badge
    live_only: bool = False                       # if True, tool needs DB (won't work in demo mode)


class ToolRegistry:
    """Singleton registry. Tools register themselves at import time via
    `register()`. Discovery queries (`list_by_capability`, `find`) read
    from this in-memory index — no DB hit, no LLM call.

    In Phase 2, this also becomes the policy enforcement point: a tool
    call goes through `Registry.authorize(tool_name, agent_key, args)`
    which checks capability match + approval flag + risk level.
    """

    _instance: "ToolRegistry | None" = None

    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    @classmethod
    def get(cls) -> "ToolRegistry":
        """Return the singleton instance (use this from call sites)."""
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    def register(self, entry: ToolEntry) -> None:
        """Register a tool. Idempotent — re-registering updates the entry."""
        if entry.name in self._tools and self._tools[entry.name] != entry:
            logger.debug(f"ToolRegistry: re-registering '{entry.name}'")
        self._tools[entry.name] = entry

    def find_by_name(self, name: str) -> Optional[ToolEntry]:
        """Return the entry registered under `name`, or None."""
        return self._tools.get(name)

    def all(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def list_by_capability(self, capability: str) -> list[ToolEntry]:
        """All tools whose `capabilities` tuple contains `capability`."""
        return [e for e in self._tools.values() if capability in e.capabilities]

    def find(self, query: str) -> list[ToolEntry]:
        """Case-insensitive substring search over name + description +
        capabilities. Used by the `discover_tools_tool` agent-facing tool."""
        q = query.lower().strip()
        if not q:
            return self.all()
        hits = []
        for e in self._tools.values():
            haystack = (e.name + " " + e.description + " " + " ".join(e.capabilities)).lower()
            if q in haystack:
                hits.append(e)
        return hits

    def approve_required(self, name: str) -> bool:
        e = self.find_by_name(name)
        return e.requires_approval if e else False


# ─── Module-level convenience ──────────────────────────────────────────────

def register(name: str, description: str, capabilities: list[str] | tuple[str, ...],
             owner_agents: list[str] | tuple[str, ...] = (),
             requires_approval: bool = False, risk_level: str = "low",
             live_only: bool = False) -> ToolEntry:
    """Sugar so callers don't need to import ToolEntry. Returns the
    registered entry so call sites can hold a reference if they want."""
    entry = ToolEntry(
        name=name,
        description=description,
        capabilities=tuple(capabilities),
        owner_agents=tuple(owner_agents),
        requires_approval=requires_approval,
        risk_level=risk_level,
        live_only=live_only,
    )
    ToolRegistry.get().register(entry)
    return entry
