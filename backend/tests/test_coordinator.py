"""Tests for Coordinator (src/ai/agentic/coordinator.py)."""

from unittest.mock import patch

import pytest

from src.ai.agentic.coordinator import Coordinator
from src.ai.agentic.plan import Plan, SubTask, ToolHint
from src.ai.agentic.worker import SubTaskResult


@pytest.fixture(autouse=True)
def patch_worker():
    """Patch Worker.execute so tests don't need real agents."""
    with patch("src.ai.agentic.coordinator.Worker.execute") as mock:
        mock.return_value = SubTaskResult(
            agent_key="HAKIM", description="Mocked", result="Mock OK", status="success",
        )
        yield


def _make_plan(subtasks=None):
    if subtasks is None:
        subtasks = [
            SubTask(
                id="sub_1",
                description="Status platform",
                agent_key="HAKIM",
                success_criteria="Return platform status",
                required_capabilities=["platform.status"],
                tool_hints=[ToolHint(tool_name="DB Platform Status", reason="Check status")],
                depends_on=[],
                parallelizable=False,
                approval_required=False,
                max_tool_calls=3,
            ),
        ]
    return Plan(
        intent="Cek status platform",
        complexity="simple",
        success_criteria="Berikan status platform dalam 1-2 ayat.",
        subtasks=subtasks,
    )


class TestCoordinator:
    def test_execute_simple_plan(self):
        """A simple plan with one subtask executes successfully."""
        plan = _make_plan()
        events = []

        coord = Coordinator(plan=plan, on_event=lambda t, p: events.append((t, p)))
        results = coord.execute()

        assert len(results) == 1
        # Even though execution will fail (HAKIM might not be available),
        # the Coordinator should still process it and return a result.
        assert results[0].agent_key == "HAKIM"

        # Should have emitted a plan event
        plan_events = [e for e in events if e[0] == "plan"]
        assert len(plan_events) >= 1

    def test_emits_plan_event(self):
        plan = _make_plan()
        events = []

        coord = Coordinator(plan=plan, on_event=lambda t, p: events.append((t, p)))
        coord.execute()

        plan_payloads = [p for t, p in events if t == "plan"]
        assert len(plan_payloads) == 1
        assert "intent" in plan_payloads[0]
        assert "complexity" in plan_payloads[0]
        assert "subtasks" in plan_payloads[0]

    def test_multiple_subtasks(self):
        subtasks = [
            SubTask(
                id="sub_1",
                description="Step one",
                agent_key="MAYA",
                success_criteria="Do step one",
                depends_on=[],
                parallelizable=False,
                approval_required=False,
                max_tool_calls=2,
            ),
            SubTask(
                id="sub_2",
                description="Step two",
                agent_key="HAKIM",
                success_criteria="Do step two",
                depends_on=["sub_1"],
                parallelizable=False,
                approval_required=False,
                max_tool_calls=2,
            ),
        ]
        plan = _make_plan(subtasks)

        with patch("src.ai.agentic.coordinator.Worker.execute") as mock_worker:
            from src.ai.agentic.worker import SubTaskResult
            results_map = {
                "MAYA": SubTaskResult(agent_key="MAYA", description="Step one", result="OK", status="success"),
                "HAKIM": SubTaskResult(agent_key="HAKIM", description="Step two", result="OK", status="success"),
            }
            mock_worker.side_effect = lambda st, model, org_id=None: results_map[st.agent_key]

            coord = Coordinator(plan=plan)
            results = coord.execute()

        assert len(results) == 2
        assert results[0].agent_key == "MAYA"
        assert results[1].agent_key == "HAKIM"


class TestCoordinatorApproval:
    def test_skipped_when_rejected(self):
        subtask = SubTask(
            id="sub_1",
            description="Delete product",
            agent_key="NEXUS",
            success_criteria="Delete the product",
            approval_required=True,
        )
        plan = _make_plan([subtask])

        with patch("src.ai.agentic.coordinator.Coordinator._request_approval", return_value=False):
            coord = Coordinator(plan=plan)
            results = coord.execute()

        assert len(results) == 1
        assert results[0].status == "skipped"

    def test_proceeds_when_approved(self):
        subtask = SubTask(
            id="sub_1",
            description="Update business profile",
            agent_key="ADILA",
            success_criteria="Update the profile",
            approval_required=True,
        )
        plan = _make_plan([subtask])

        with patch("src.ai.agentic.coordinator.Coordinator._request_approval", return_value=True):
            coord = Coordinator(plan=plan)
            results = coord.execute()

        assert len(results) == 1
        assert results[0].status == "success"


class TestCoordinatorCancellation:
    def test_stops_dispatching_once_cancelled(self):
        """A Stop click sets should_stop() true. The Coordinator must not
        dispatch any more subtasks after that point, even mid-plan —
        already-produced results are kept, not discarded."""
        subtasks = [
            SubTask(id="sub_1", description="Step one", agent_key="MAYA",
                    success_criteria="Do step one", depends_on=[]),
            SubTask(id="sub_2", description="Step two", agent_key="HAKIM",
                    success_criteria="Do step two", depends_on=["sub_1"]),
            SubTask(id="sub_3", description="Step three", agent_key="ZARA",
                    success_criteria="Do step three", depends_on=["sub_2"]),
        ]
        plan = _make_plan(subtasks)

        # Cancel right after the first subtask completes.
        stop_flag = {"stop": False}

        def _fake_execute(st, model, org_id=None):
            if st.id == "sub_1":
                stop_flag["stop"] = True
                return SubTaskResult(agent_key="MAYA", description="Step one", result="OK", status="success")
            # sub_2/sub_3 must never be reached.
            return SubTaskResult(agent_key=st.agent_key, description=st.description, result="", status="failed")

        with patch("src.ai.agentic.coordinator.Worker.execute", side_effect=_fake_execute):
            coord = Coordinator(plan=plan, should_stop=lambda: stop_flag["stop"])
            results = coord.execute()

        assert len(results) == 1
        assert results[0].agent_key == "MAYA"
        assert results[0].status == "success"

    def test_never_dispatches_when_already_cancelled(self):
        plan = _make_plan()
        with patch("src.ai.agentic.coordinator.Worker.execute") as mock_worker:
            coord = Coordinator(plan=plan, should_stop=lambda: True)
            results = coord.execute()

        mock_worker.assert_not_called()
        assert results == []
