import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.agents.tool_mappings import get_tools, STATIC_TOOL_MAPPINGS
from src.ai.tools import (
    product_pricing_tool,
    contact_info_tool,
    conversation_history_tool,
    system_documentation_tool,
    db_upsert_lead_tool,
    workflow_generate_quotation_tool,
)


# ─── Per-agent tool list ────────────────────────────────────────────────────

def test_every_agent_in_registry_has_a_list():
    from src.core.constants import AGENTS
    for key in AGENTS:
        assert key in STATIC_TOOL_MAPPINGS, f"Agent {key} missing from STATIC_TOOL_MAPPINGS"
        assert isinstance(STATIC_TOOL_MAPPINGS[key], list)


def test_claudia_has_no_execution_tools():
    assert STATIC_TOOL_MAPPINGS["CLAUDIA"] == []


def test_maya_has_pricing_and_workflow_tools():
    maya = STATIC_TOOL_MAPPINGS["MAYA"]
    assert product_pricing_tool in maya
    assert contact_info_tool in maya
    assert conversation_history_tool in maya
    assert db_upsert_lead_tool in maya
    assert workflow_generate_quotation_tool in maya


def test_hakim_has_system_docs():
    assert system_documentation_tool in STATIC_TOOL_MAPPINGS["HAKIM"]


def test_get_tools_for_unknown_key_returns_empty_list():
    assert get_tools("DOES_NOT_EXIST") == []


# ─── Image generation (upstream) ────────────────────────────────────────────

def test_danish_gets_image_tool_only_when_collector_supplied():
    without_collector = get_tools("DANISH", artifact_collector=None)
    with_collector = get_tools("DANISH", artifact_collector=[])

    assert without_collector == [t for t in without_collector if t.name != "Image Generation"]
    assert any(t.name == "Image Generation" for t in with_collector)
    assert len(with_collector) > len(without_collector)


def test_other_agents_never_get_image_tool():
    for agent_key in ["ZARA", "AIMAN", "AMELIA", "ADILA", "CLAUDIA", "MAYA", "HAKIM"]:
        tools = get_tools(agent_key, artifact_collector=[])
        assert all(t.name != "Image Generation" for t in tools), (
            f"{agent_key} unexpectedly has Image Generation tool"
        )


def test_maya_static_tools_unaffected_by_collector():
    maya_tools = get_tools("MAYA", artifact_collector=[])
    assert product_pricing_tool in maya_tools
    assert contact_info_tool in maya_tools
    assert conversation_history_tool in maya_tools
    assert all(t.name != "Image Generation" for t in maya_tools)
