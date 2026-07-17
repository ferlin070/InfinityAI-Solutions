import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.agents.tool_mappings import get_tools


def test_danish_gets_image_tool_only_when_collector_supplied():
    without_collector = get_tools("DANISH", artifact_collector=None)
    with_collector = get_tools("DANISH", artifact_collector=[])

    assert without_collector == []
    assert len(with_collector) == 1
    assert with_collector[0].name == "Image Generation"


def test_other_agents_never_get_image_tool():
    for agent_key in ["ZARA", "AIMAN", "AMELIA", "ADILA", "CLAUDIA"]:
        tools = get_tools(agent_key, artifact_collector=[])
        assert all(t.name != "Image Generation" for t in tools)


def test_static_tools_unaffected_by_collector():
    maya_tools = get_tools("MAYA", artifact_collector=[])
    assert len(maya_tools) == 3
    assert all(t.name != "Image Generation" for t in maya_tools)
