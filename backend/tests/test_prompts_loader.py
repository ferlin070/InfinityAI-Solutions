import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.prompts.loader import resolve_role_goal_backstory
from src.core.constants import AGENTS


def test_all_agent_keys_have_a_mapping():
    for key in AGENTS:
        role, goal, backstory = resolve_role_goal_backstory(key)
        assert role and goal and backstory


def test_claudia_backstory_preserves_json_routing_format():
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    assert '"status": "accepted"' in backstory
    assert '"assignments"' in backstory
    assert "JSON" in backstory


def test_claudia_backstory_preserves_routing_rule_forbidding_danish_for_sales():
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    assert "JANGAN hantar tugasan JUALAN kepada DANISH" in backstory


def test_claudia_backstory_has_chat_escape_hatch_before_rejection():
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    assert '"status": "chat"' in backstory
    assert '"status": "rejected"' in backstory
    # "chat" must be presented before "rejected" so Claudia treats it as the
    # default fallback for ambiguous messages, not outright refusal.
    assert backstory.index('"status": "chat"') < backstory.index('"status": "rejected"')


def test_danish_backstory_preserves_helpful_tone():
    _, _, backstory = resolve_role_goal_backstory("DANISH")
    assert "mesra" in backstory
    assert "helpful" in backstory
    assert "copywriting" in backstory


def test_danish_backstory_requires_image_tool_for_visual_requests():
    _, _, backstory = resolve_role_goal_backstory("DANISH")
    assert "Image Generation tool" in backstory
    # Must explicitly forbid the failure mode observed in production: writing
    # banner *copy* instead of actually calling the image tool.
    assert "JANGAN" in backstory


def test_lowercase_key_is_normalized():
    upper = resolve_role_goal_backstory("ZARA")
    lower = resolve_role_goal_backstory("zara")
    assert upper == lower


def test_unknown_key_raises_key_error():
    with pytest.raises(KeyError):
        resolve_role_goal_backstory("NOBODY")
