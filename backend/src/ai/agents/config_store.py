import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

_STORE_PATH = os.path.join(os.path.dirname(__file__), "_agent_overrides.json")


@dataclass
class AgentOverride:
    provider: str | None = None
    model: str | None = None
    role: str | None = None
    goal: str | None = None
    backstory: str | None = None


class AgentConfigStore:
    """In-memory override store persisted to a JSON file.

    MVP approach — replaced by the `agent_configurations` DB table once the
    other dev applies 0002_agent_configs.sql. Works immediately for demo.
    """

    def __init__(self):
        self._overrides: dict[str, dict[str, AgentOverride]] = {}  # org_id → agent_key → override
        self._load()

    def get(self, org_id: str, agent_key: str) -> AgentOverride | None:
        return self._overrides.get(org_id, {}).get(agent_key.upper())

    def get_all(self, org_id: str) -> dict[str, AgentOverride]:
        return dict(self._overrides.get(org_id, {}))

    def set(self, org_id: str, agent_key: str, override: AgentOverride) -> None:
        self._overrides.setdefault(org_id, {})[agent_key.upper()] = override
        self._save()

    def delete(self, org_id: str, agent_key: str) -> None:
        self._overrides.get(org_id, {}).pop(agent_key.upper(), None)
        self._save()

    def _load(self) -> None:
        try:
            with open(_STORE_PATH) as f:
                raw = json.load(f)
                for org_id, agents in raw.items():
                    for key, vals in agents.items():
                        self._overrides.setdefault(org_id, {})[key] = AgentOverride(**vals)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self) -> None:
        raw = {
            org_id: {key: asdict(ov) for key, ov in agents.items()}
            for org_id, agents in self._overrides.items()
        }
        with open(_STORE_PATH, "w") as f:
            json.dump(raw, f, indent=2)


_store = AgentConfigStore()


def get_agent_config_store() -> AgentConfigStore:
    return _store
