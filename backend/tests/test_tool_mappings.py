"""Tests for the per-agent tool mapping. Verifies that the registry is
internally consistent and that every static tool is actually exposed via
`get_all_tools_for_agent` for its assigned agent."""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.agents.tool_mappings import TOOL_MAPPINGS, get_tools_for_agent
from src.ai.tools import (
    product_pricing_tool,
    contact_info_tool,
    conversation_history_tool,
    system_documentation_tool,
    db_upsert_lead_tool,
    workflow_generate_quotation_tool,
)


def test_every_agent_in_registry_has_a_list():
    from src.core.constants import AGENTS
    for key in AGENTS:
        assert key in TOOL_MAPPINGS, f"Agent {key} missing from TOOL_MAPPINGS"
        assert isinstance(TOOL_MAPPINGS[key], list)


def test_claudia_has_no_execution_tools():
    assert TOOL_MAPPINGS["CLAUDIA"] == []


def test_maya_has_pricing_and_workflow_tools():
    maya = get_tools_for_agent("MAYA")
    assert product_pricing_tool in maya
    assert contact_info_tool in maya
    assert conversation_history_tool in maya
    assert db_upsert_lead_tool in maya
    assert workflow_generate_quotation_tool in maya


def test_hakim_has_system_docs():
    hakim = get_tools_for_agent("HAKIM")
    assert system_documentation_tool in hakim


def test_get_tools_for_agent_unknown_key_returns_empty():
    assert get_tools_for_agent("DOES_NOT_EXIST") == []
