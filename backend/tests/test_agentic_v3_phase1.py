"""Tests for the agentic-v3 Phase 1 layer:
- Plan / SubTask / ToolHint Pydantic models
- ExecutionTrace / SubTaskTrace / Observation / Validation
- ToolRegistry queryable catalog
- Planner LLM-call (with scripted provider)
- RetryEngine (transient retry + alt-tool fallback)
- REFLECTION_TEMPLATE integration into specialist backstories
"""

import sys, os
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── Plan / SubTask ────────────────────────────────────────────────────────

def test_plan_basic_construction():
    from src.ai.agentic.plan import Plan, SubTask, ToolHint
    plan = Plan(
        intent="Bos nak tahu status WhatsApp",
        complexity="simple",
        subtasks=[
            SubTask(
                id="sub_1",
                description="Semak status WhatsApp",
                agent_key="HAKIM",
                success_criteria="Kembalikan status tersambung / tidak",
                required_capabilities=["platform.status"],
                tool_hints=[ToolHint(tool_name="DB Platform Status", reason="Aggregated")],
            ),
        ],
        success_criteria="Balas dengan status",
    )
    assert plan.intent.startswith("Bos")
    assert plan.complexity == "simple"
    assert len(plan.subtasks) == 1
    assert plan.subtask_by_id("sub_1") is not None
    assert plan.subtask_by_id("missing") is None


def test_plan_ready_subtasks_respects_dependencies():
    from src.ai.agentic.plan import Plan, SubTask
    plan = Plan(
        intent="test", complexity="moderate",
        subtasks=[
            SubTask(id="a", description="a", agent_key="MAYA", success_criteria="x"),
            SubTask(id="b", description="b", agent_key="HAKIM", success_criteria="x", depends_on=["a"]),
            SubTask(id="c", description="c", agent_key="DANISH", success_criteria="x", depends_on=["a"]),
        ],
        success_criteria="x",
    )
    # No subtasks completed -> only 'a' is ready
    ready = plan.ready_subtasks(set())
    assert [s.id for s in ready] == ["a"]
    # After 'a' completes -> 'b' and 'c' are ready
    ready = plan.ready_subtasks({"a"})
    assert {s.id for s in ready} == {"b", "c"}


# ─── ToolRegistry ──────────────────────────────────────────────────────────

def test_registry_register_and_get():
    from src.ai.agentic.registry import ToolRegistry, register
    # Import tool_mappings first so the production tool registrations
    # have run; otherwise the registry is empty.
    import src.ai.agents.tool_mappings  # noqa: F401
    reg = ToolRegistry.get()
    entry = register(
        "Test Tool Phase1", "A test tool.",
        capabilities=["test"], owner_agents=("HAKIM",),
        requires_approval=True, risk_level="high",
    )
    assert entry.name == "Test Tool Phase1"
    got = reg.find_by_name("Test Tool Phase1")
    assert got is not None
    assert got.requires_approval is True
    assert got.risk_level == "high"


def test_registry_list_by_capability():
    # Import tool_mappings so the production tool registrations have run.
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.agentic.registry import ToolRegistry
    reg = ToolRegistry.get()
    crm_reads = reg.list_by_capability("crm.read")
    names = {e.name for e in crm_reads}
    # These tools are registered in tool_mappings.py at import time
    assert "Contact Info" in names
    assert "Conversation History" in names
    assert "DB List Contacts" in names


def test_registry_find_by_substring():
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.agentic.registry import ToolRegistry
    reg = ToolRegistry.get()
    hits = reg.find("lead")
    names = {e.name for e in hits}
    # Lead-related tools should be in the hit list
    assert any("Lead" in n for n in names)


def test_registry_requires_approval_set_for_destructive_tools():
    """Destructive tools (delete, update sensitive) must be flagged
    for approval — Phase 3 will gate execution behind human checkpoints."""
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.agentic.registry import ToolRegistry
    reg = ToolRegistry.get()
    assert reg.approve_required("DB Approve Quotation") is True
    assert reg.approve_required("DB Update Business Profile") is True
    assert reg.approve_required("Product Pricing") is False
    assert reg.approve_required("DB List Leads") is False


# ─── RetryEngine ───────────────────────────────────────────────────────────

def test_retry_engine_retries_transient_then_succeeds():
    from src.ai.agentic.retry import RetryEngine
    engine = RetryEngine(max_retries=2, initial_backoff_s=0.0, backoff_factor=1.0)
    calls = []

    def call_fn(tool_name):
        calls.append(tool_name)
        if len(calls) < 3:
            return False, "", "rate limit exceeded"  # transient
        return True, "ok", None

    result = engine.execute_with_retry("Test", call_fn)
    assert result.success
    assert result.attempts == 3
    assert result.output == "ok"


def test_retry_engine_falls_back_to_alt_tool_on_permanent_failure():
    from src.ai.agentic.retry import RetryEngine
    engine = RetryEngine(
        max_retries=0,  # no retry, just fall back immediately
        alt_tools={"Primary": "Secondary"},
    )
    calls = []

    def call_fn(tool_name):
        calls.append(tool_name)
        if tool_name == "Primary":
            return False, "", "argument error"  # permanent
        return True, "from-secondary", None

    result = engine.execute_with_retry("Primary", call_fn)
    assert result.success
    assert result.fell_back_to == "Secondary"
    assert calls == ["Primary", "Secondary"]


def test_retry_engine_gives_up_after_exhausted():
    from src.ai.agentic.retry import RetryEngine
    # max_retries=0 -> no retry, just fall back to alt immediately
    engine = RetryEngine(max_retries=0, initial_backoff_s=0.0,
                         alt_tools={"Primary": "Secondary"})
    calls = []

    def call_fn(tool_name):
        calls.append(tool_name)
        return False, "", "boom"  # permanent error

    result = engine.execute_with_retry("Primary", call_fn)
    assert not result.success
    assert "boom" in (result.error or "")
    # Tried Primary, then fell back to Secondary, then no more alts -> gave up
    assert calls == ["Primary", "Secondary"], f"Expected primary then secondary, got {calls}"


def test_retry_engine_emits_events():
    from src.ai.agentic.retry import RetryEngine
    engine = RetryEngine(max_retries=2, initial_backoff_s=0.0, backoff_factor=1.0)
    events = []

    def call_fn(tool_name):
        if len(events) < 2:
            return False, "", "rate limit"
        return True, "ok", None

    def on_event(event_type, payload):
        events.append((event_type, payload))

    engine.execute_with_retry("Test", call_fn, on_event=on_event)
    event_types = [e[0] for e in events]
    assert "tool_retry" in event_types
    assert "tool_fallback" not in event_types  # no fallback happened


# ─── Planner ───────────────────────────────────────────────────────────────

def test_planner_fallback_plan_always_valid():
    """When the LLM output can't be parsed, the Planner returns a safe
    fallback (route to NEXUS) so the user always gets an executable plan."""
    from src.ai.agentic.plan import Plan
    from src.ai.providers.base import LLMResult

    class BadProvider:
        def complete(self, *a, **k):
            return LLMResult(text="", tokens_in=0, tokens_out=0, cost_usd=0,
                              duration_ms=0, model="x", provider="openai")
        # InfinityLLMAdapter.call() always goes through stream_complete now
        # (see LLMProvider.stream_complete's default docstring) — this fake
        # doesn't subclass LLMProvider so it doesn't inherit that default.
        def stream_complete(self, messages, model, temperature=0.7, max_tokens=4096,
                             tools=None, on_delta=None, should_stop=None):
            return self.complete(messages, model, temperature, max_tokens, tools)

    from src.ai.agentic.planner import Planner
    from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
    p = Planner()
    p._llm = InfinityLLMAdapter(provider=BadProvider(), model="x", agent_key="PLANNER", org_id=None)
    plan = p.plan("test prompt")
    assert isinstance(plan, Plan)
    assert len(plan.subtasks) >= 1
    assert plan.subtasks[0].agent_key == "NEXUS"


def test_planner_parses_valid_json_output():
    from src.ai.agentic.plan import Plan
    from src.ai.providers.base import LLMResult

    valid_json = """
    {
      "intent": "Bos nak tahu status WhatsApp",
      "complexity": "simple",
      "success_criteria": "Kembalikan status",
      "subtasks": [
        {
          "id": "sub_1",
          "description": "Semak status",
          "agent_key": "HAKIM",
          "success_criteria": "Kembalikan status",
          "required_capabilities": ["platform.status"],
          "tool_hints": [],
          "depends_on": [],
          "parallelizable": false,
          "approval_required": false,
          "max_tool_calls": 3
        }
      ]
    }
    """

    class GoodProvider:
        def __init__(self):
            self.calls = 0
        def complete(self, *a, **k):
            self.calls += 1
            return LLMResult(text=valid_json, tokens_in=10, tokens_out=20, cost_usd=0.001,
                              duration_ms=100, model="x", provider="openai")
        def stream_complete(self, messages, model, temperature=0.7, max_tokens=4096,
                             tools=None, on_delta=None, should_stop=None):
            return self.complete(messages, model, temperature, max_tokens, tools)

    from src.ai.agentic.planner import Planner
    from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
    p = Planner()
    p._llm = InfinityLLMAdapter(provider=GoodProvider(), model="x", agent_key="PLANNER", org_id=None)
    plan = p.plan("adakah kita sudah bersambung dengan whatsapp?")
    assert plan.intent == "Bos nak tahu status WhatsApp"
    assert plan.complexity == "simple"
    assert len(plan.subtasks) == 1
    assert plan.subtasks[0].agent_key == "HAKIM"


def test_planner_parses_json_inside_code_fence():
    from src.ai.agentic.plan import Plan
    from src.ai.providers.base import LLMResult

    fenced = 'Here is the plan:\n```json\n{"intent":"x","complexity":"simple","subtasks":[{"id":"sub_1","description":"d","agent_key":"MAYA","success_criteria":"s","required_capabilities":[],"tool_hints":[],"depends_on":[],"parallelizable":false,"approval_required":false,"max_tool_calls":3}],"success_criteria":"s"}\n```\nDone.'

    class FencedProvider:
        def complete(self, *a, **k):
            return LLMResult(text=fenced, tokens_in=10, tokens_out=20, cost_usd=0.001,
                              duration_ms=100, model="x", provider="openai")
        def stream_complete(self, messages, model, temperature=0.7, max_tokens=4096,
                             tools=None, on_delta=None, should_stop=None):
            return self.complete(messages, model, temperature, max_tokens, tools)

    from src.ai.agentic.planner import Planner
    from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
    p = Planner()
    p._llm = InfinityLLMAdapter(provider=FencedProvider(), model="x", agent_key="PLANNER", org_id=None)
    plan = p.plan("test")
    assert plan.intent == "x"
    assert plan.subtasks[0].agent_key == "MAYA"


# ─── Reflection template integration ────────────────────────────────────────

def test_every_specialist_includes_reflection_template():
    """The shared REFLECTION_TEMPLATE must be in every specialist's
    backstory so they all follow the same reasoning discipline."""
    from src.ai.prompts.loader import resolve_role_goal_backstory
    for key in ("MAYA", "HAKIM", "ZARA", "DANISH", "AIMAN", "AMELIA", "ADILA", "NEXUS"):
        _, _, backstory = resolve_role_goal_backstory(key)
        assert "RANCANG" in backstory or "REFLEK" in backstory, (
            f"{key} backstory missing the shared REFLECTION_TEMPLATE"
        )


# ─── discover_tools_tool ────────────────────────────────────────────────────

def test_discover_tools_tool_returns_catalog():
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.tools.tool_registry import discover_tools_tool
    out = discover_tools_tool.run()
    assert "count" in out
    assert "tools" in out
    assert "grouped_by_capability" in out


def test_discover_tools_tool_filters_by_capability():
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.tools.tool_registry import discover_tools_tool
    out = discover_tools_tool.run(capability="crm.read")
    assert "Contact Info" in out or "DB List Contacts" in out


def test_discover_tools_tool_filters_by_query():
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.tools.tool_registry import discover_tools_tool
    out = discover_tools_tool.run(query="lead")
    assert "Lead" in out


def test_discover_tools_tool_filters_by_owner_agent():
    import src.ai.agents.tool_mappings  # noqa: F401
    from src.ai.tools.tool_registry import discover_tools_tool
    out = discover_tools_tool.run(owner_agent="HAKIM")
    # HAKIM's tools should include System Documentation
    assert "System Documentation" in out
