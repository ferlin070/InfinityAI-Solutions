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


def test_build_crewai_agent_gives_danish_image_tool_when_collector_supplied():
    config = load_agent("DANISH")
    agent = build_crewai_agent(config, llm=MagicMock(), artifact_collector=[])

    assert any(t.name == "Image Generation" for t in agent.tools)


def test_build_crewai_agent_omits_image_tool_without_collector():
    config = load_agent("DANISH")
    agent = build_crewai_agent(config, llm=MagicMock())

    assert agent.tools == []


def test_build_crewai_agent_threads_on_event_into_internally_built_llm():
    config = load_agent("ZARA")
    events = []

    with patch("src.ai.agents.factory.resolve_provider", return_value=MagicMock()):
        agent = build_crewai_agent(config, on_event=lambda t, p: events.append((t, p)))

    assert agent.llm._on_event is not None
