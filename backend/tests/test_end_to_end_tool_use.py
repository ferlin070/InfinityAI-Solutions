"""End-to-end test: when the user asks 'adakah kita sudah bersambung
dengan WhatsApp?', the agent MUST use a tool (not just chat).

We can't run the real LLM in tests, but we can use a scripted provider
that returns a tool_call, and verify the adapter's tool loop executes
it and surfaces the result. This is the same machinery the production
flow uses.
"""
import sys, os
import json
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ai.providers.base import LLMResult
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter


class ScriptedProvider:
    """Provider that returns a tool_call on the first request, then a
    plain text on the second. Mirrors what the LLM should do when a
    user asks a status question and a DB tool is available."""
    def __init__(self):
        self.calls = []

    def complete(self, messages, model, temperature=0.7, max_tokens=4096, tools=None):
        self.calls.append({"n": len(self.calls) + 1, "tools": tools})
        if len(self.calls) == 1:
            # First call: LLM should call the platform-status tool
            assert tools, "First call must offer tools to the LLM"
            tool_name = next(
                t["function"]["name"] for t in tools
                if "Platform" in t["function"]["name"] or "platform" in t["function"]["name"].lower()
            )
            return LLMResult(
                text="", tokens_in=10, tokens_out=5, cost_usd=0.001,
                duration_ms=100, model=model, provider="openai",
                tool_calls=[{
                    "id": "call_1",
                    "function": {"name": tool_name, "arguments": "{}"},
                }],
            )
        # Second call: final answer based on the tool's result
        return LLMResult(
            text="WhatsApp sedang TIDAK DISAMBUNG (demo mode: DB tidak dikonfigurasikan). Untuk setup, pergi ke Settings > WhatsApp Connection.",
            tokens_in=10, tokens_out=20, cost_usd=0.002,
            duration_ms=200, model=model, provider="openai",
        )

    def stream(self, *args, **kwargs):
        yield ""


def test_user_asking_whatsapp_status_triggers_a_tool_call():
    """Reproduce the user-reported failure and verify the fix: a
    status-style question must result in a tool call, not a chat-only
    response. Uses the real InfinityLLMAdapter's tool-loop machinery."""
    from src.ai.agents.factory import build_crewai_agent
    from src.ai.agents.registry import load_agent
    from src.ai.agents.tool_mappings import get_tools
    from crewai import Crew, Process, Task

    provider = ScriptedProvider()
    captured = []

    # Build a Claudia agent with the real quick-check toolset. Capture
    # `on_event` to verify the tool call shows up as an event the UI
    # would render ("Claudia sedang guna DB Platform Status...").
    def on_event(event_type, payload):
        captured.append((event_type, payload))

    llm = InfinityLLMAdapter(
        provider=provider,
        model="gpt-4o-mini",
        agent_key="CLAUDIA",
        org_id=None,
        on_event=on_event,
    )
    config = load_agent("CLAUDIA")
    agent = build_crewai_agent(config, llm=llm, artifact_collector=[])

    # Confirm the agent has the platform tool available.
    tool_names = [t.name for t in get_tools("CLAUDIA")]
    assert "DB Platform Status" in tool_names

    task = Task(
        description="adakah kita sudah bersambung dengan whatsapp?",
        expected_output="Balas dengan data tool.",
        agent=agent,
    )
    Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()

    # The tool loop should have:
    # 1. offered tools on the first call
    # 2. received a tool_call from the "LLM" (our ScriptedProvider)
    # 3. fired a tool_call start event
    # 4. fired a tool_call done event
    # 5. got the final answer
    assert len(provider.calls) == 2, f"Expected 2 LLM calls (tool + final), got {len(provider.calls)}"
    assert provider.calls[0]["tools"], "First call should have offered tools"

    event_types = [e[0] for e in captured]
    assert "tool_call" in event_types, (
        f"Tool was called but no tool_call event fired — UI won't show progress. "
        f"Events: {captured}"
    )
    # The tool_call event should name the right tool
    tool_call_events = [e for e in captured if e[0] == "tool_call"]
    assert any("Platform" in e[1].get("tool", "") for e in tool_call_events), (
        f"Expected DB Platform Status to be the tool called. Events: {captured}"
    )
