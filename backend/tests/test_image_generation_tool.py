import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.tools.image_generation import build_image_generation_tool


def _fake_openai_client(b64="ZmFrZQ=="):
    client = MagicMock()
    resp = MagicMock()
    resp.data = [MagicMock(b64_json=b64)]
    client.images.generate.return_value = resp
    return client


def test_image_tool_appends_artifact_and_returns_short_confirmation():
    collector = []
    tool = build_image_generation_tool(collector)

    with patch("src.ai.tools.image_generation.OpenAI", return_value=_fake_openai_client("ZmFrZQ==")):
        result = tool.func("banner promosi jualan raya")

    assert len(collector) == 1
    assert collector[0] == {
        "type": "image",
        "mime_type": "image/png",
        "data_base64": "ZmFrZQ==",
        "caption": "banner promosi jualan raya",
    }
    # The base64 payload must never re-enter the LLM's context via the tool's
    # return value — only the short confirmation string does.
    assert "ZmFrZQ==" not in result
    assert "berjaya dijana" in result


def test_image_tool_each_call_gets_isolated_collector():
    collector_a, collector_b = [], []
    tool_a = build_image_generation_tool(collector_a)
    tool_b = build_image_generation_tool(collector_b)

    with patch("src.ai.tools.image_generation.OpenAI", return_value=_fake_openai_client("aaa")):
        tool_a.func("banner A")
    with patch("src.ai.tools.image_generation.OpenAI", return_value=_fake_openai_client("bbb")):
        tool_b.func("banner B")

    assert [a["data_base64"] for a in collector_a] == ["aaa"]
    assert [a["data_base64"] for a in collector_b] == ["bbb"]


def test_image_tool_handles_provider_errors_gracefully():
    collector = []
    tool = build_image_generation_tool(collector)
    broken_client = MagicMock()
    broken_client.images.generate.side_effect = RuntimeError("API down")

    with patch("src.ai.tools.image_generation.OpenAI", return_value=broken_client):
        result = tool.func("banner")

    assert collector == []
    assert "Gagal menjana imej" in result
