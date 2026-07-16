import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.agents.factory import build_crewai_agent
from src.ai.agents.registry import load_agent
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter


def test_build_crewai_agent_uses_config_role_goal_backstory():
    config = load_agent("ZARA")
    agent = build_crewai_agent(config, llm=MagicMock())

    assert agent.role == config.role
    assert agent.goal == config.goal
    assert agent.backstory == config.backstory


def test_build_crewai_agent_disallows_delegation():
    config = load_agent("CLAUDIA")
    agent = build_crewai_agent(config, llm=MagicMock())

    assert agent.allow_delegation is False


def test_build_crewai_agent_builds_llm_when_not_provided():
    config = load_agent("ZARA")

    with patch("src.ai.agents.factory.resolve_provider") as mock_resolve:
        mock_resolve.return_value = MagicMock()
        agent = build_crewai_agent(config)

    mock_resolve.assert_called_once_with(config.provider, config.org_id)
    assert isinstance(agent.llm, InfinityLLMAdapter)
    assert agent.llm.model == config.model
