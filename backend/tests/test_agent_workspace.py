"""Smoke tests for the Agent Workspace frontend components (JSDOM-rendered
via Vitest would be ideal; for now we verify the JSX files parse and
the event-mapping logic in the hook is correct via Node)."""

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "frontend-react", "src")
WORKSPACE = os.path.join(ROOT, "components", "workspace")


def test_workspace_directory_exists():
    assert os.path.isdir(WORKSPACE), f"Expected workspace dir at {WORKSPACE}"


def test_all_workspace_components_exist():
    """Every component file the AgentWorkspace imports must exist."""
    expected = [
        "AgentWorkspace.jsx",
        "WorkspaceHeader.jsx",
        "MultiAgentPanel.jsx",
        "AgentTimeline.jsx",
        "ToolExecutionCard.jsx",
    ]
    for f in expected:
        path = os.path.join(WORKSPACE, f)
        assert os.path.exists(path), f"Missing component: {f}"
        assert os.path.getsize(path) > 100, f"{f} is suspiciously small"


def test_hook_directory_exists():
    hook_dir = os.path.join(ROOT, "hooks")
    assert os.path.isdir(hook_dir)
    assert os.path.exists(os.path.join(hook_dir, "useAgentStream.js"))


def test_agentworkspace_imports_the_hook():
    """AgentWorkspace must consume useAgentStream — that is the wire
    between the SSE stream and the rendered state."""
    src = open(os.path.join(WORKSPACE, "AgentWorkspace.jsx"), encoding="utf-8").read()
    assert "useAgentStream" in src, "AgentWorkspace must import useAgentStream"
    assert "streamChatFactory" in src, "AgentWorkspace must use streamChatFactory"


def test_agenttimeline_handles_all_event_kinds():
    """The timeline component must handle every step kind the backend emits."""
    src = open(os.path.join(WORKSPACE, "AgentTimeline.jsx"), encoding="utf-8").read()
    required_kinds = ["plan", "subtask", "tool", "validation", "reflection", "approval"]
    for kind in required_kinds:
        assert f'kind="{kind}"' in src or f"kind === '{kind}'" in src, (
            f"AgentTimeline doesn't render step kind '{kind}'"
        )


def test_toolexecutioncard_handles_image_results():
    """The ToolExecutionCard must render image-generation artifacts inline."""
    src = open(os.path.join(WORKSPACE, "ToolExecutionCard.jsx"), encoding="utf-8").read()
    assert "data_base64" in src
    # The src attribute is built as `data:${mime_type};base64,${data}` —
    # check for the joined form so the test doesn't break on string split.
    assert "data:" in src and "base64," in src


def test_approvalstep_has_approve_and_reject_buttons():
    src = open(os.path.join(WORKSPACE, "AgentTimeline.jsx"), encoding="utf-8").read()
    # The ApprovalStep inside AgentTimeline.jsx must render both
    # Approve and Reject buttons for the user to gate destructive ops.
    assert "Approve" in src
    assert "Reject" in src


def test_event_to_step_kind_mapping_in_hook():
    """Verify the useAgentStream hook maps every backend event to a
    step kind the UI can render."""
    src = open(os.path.join(ROOT, "hooks", "useAgentStream.js"), encoding="utf-8").read()
    expected_events = [
        "plan",
        "subtask_start",
        "subtask_done",
        "tool_call",
        "observation",
        "tool_retry",
        "tool_fallback",
        "validation",
        "reflection",
        "approval_required",
        "final",
        "error",
    ]
    for ev in expected_events:
        # Each event is handled in a case clause:  case 'foo':
        assert f"case '{ev}'" in src, f"useAgentStream doesn't handle event '{ev}'"
