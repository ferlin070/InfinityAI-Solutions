from dataclasses import dataclass

from src.ai.agents.config_store import get_agent_config_store
from src.ai.prompts.loader import resolve_role_goal_backstory
from src.core.constants import AGENTS

# MVP default: every agent runs OpenAI gpt-4o-mini. Per-agent overrides become a
# per-row `agents.model` value once the DB-backed registry lands (§7.1) — no
# call-site changes needed then, only this default.
_DEFAULT_PROVIDER = "openai"
_DEFAULT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class AgentConfig:
    """Shape mirrors the future `agents` DB row (docs/architecture/ai-execution-crewai.md
    §7.1) so swapping load_agents()'s data source for a real DB query later is a
    change inside this module only — no call-site changes anywhere else.
    """

    key: str
    name: str
    role: str
    goal: str
    backstory: str
    provider: str = _DEFAULT_PROVIDER
    model: str = _DEFAULT_MODEL
    org_id: str | None = None


def load_agents(org_id: str | None = None) -> dict[str, AgentConfig]:
    """Load all agent configs. MVP: sourced from src/core/constants.py (in-code
    templates, shared across all orgs). `org_id` is accepted now so a DB-backed
    per-org override becomes a change inside this function only.
    """
    return {key: _build_config(key, org_id) for key in AGENTS}


def load_agent(key: str, org_id: str | None = None) -> AgentConfig:
    key = key.upper()
    if key not in AGENTS:
        raise KeyError(f"Unknown agent key '{key}'")
    return _build_config(key, org_id)


def _build_config(key: str, org_id: str | None) -> AgentConfig:
    role, goal, backstory = resolve_role_goal_backstory(key)
    provider = _DEFAULT_PROVIDER
    model = _DEFAULT_MODEL

    if org_id:
        store = get_agent_config_store()
        override = store.get(org_id, key)
        if override:
            if override.provider:
                provider = override.provider
            if override.model:
                model = override.model
            if override.role:
                role = override.role
            if override.goal:
                goal = override.goal
            if override.backstory:
                backstory = override.backstory

    return AgentConfig(
        key=key,
        name=AGENTS[key]["name"],
        role=role,
        goal=goal,
        backstory=backstory,
        provider=provider,
        model=model,
        org_id=org_id,
    )
