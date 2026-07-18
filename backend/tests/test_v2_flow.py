"""Tests for V2 flow (src/ai/flows/task_execution_flow_v2.py)."""

from unittest.mock import patch

import pytest

from src.ai.flows.task_execution_flow_v2 import TaskExecutionFlowV2
from src.schemas.models import ExecuteResponse


class TestV2Flow:
    def test_returns_execute_response(self):
        """The V2 flow always returns an ExecuteResponse."""
        flow = TaskExecutionFlowV2()
        response = flow.run(prompt="Apa status platform?", model="gpt-4o-mini")
        assert isinstance(response, ExecuteResponse)
        assert response.model == "gpt-4o-mini"

    def test_emits_status_and_plan_events(self):
        """The V2 flow emits at least a status and plan event."""
        events = []

        flow = TaskExecutionFlowV2(on_event=lambda t, p: events.append((t, p)))
        flow.run(prompt="Cek status", model="gpt-4o-mini")

        event_types = [e[0] for e in events]
        assert "status" in event_types
        assert "plan" in event_types

    def test_success_path(self):
        """When the Coordinator returns results, the flow returns success."""
        events = []

        with patch("src.ai.agentic.planner.Planner.plan") as mock_plan:
            from src.ai.agentic.plan import Plan, SubTask

            mock_plan.return_value = Plan(
                intent="Test",
                complexity="simple",
                success_criteria="Done",
                subtasks=[
                    SubTask(id="sub_1", description="Test task", agent_key="HAKIM",
                            success_criteria="Done", approval_required=False),
                ],
            )

            with patch("src.ai.agentic.coordinator.Worker.execute") as mock_worker:
                from src.ai.agentic.worker import SubTaskResult
                mock_worker.return_value = SubTaskResult(
                    agent_key="HAKIM", description="Test", result="OK", status="success",
                )

                flow = TaskExecutionFlowV2(on_event=lambda t, p: events.append((t, p)))
                response = flow.run(prompt="Test", model="gpt-4o-mini")

        assert response.status == "success"
        assert len(response.results) == 1
        assert response.results[0].agent == "HAKIM"
        # Should have emitted a plan event
        plan_events = [e for e in events if e[0] == "plan"]
        assert len(plan_events) == 1

    def test_all_failed_returns_chat(self):
        """When every subtask fails, flow returns chat with an apology."""
        with patch("src.ai.agentic.planner.Planner.plan") as mock_plan:
            from src.ai.agentic.plan import Plan, SubTask

            mock_plan.return_value = Plan(
                intent="Test",
                complexity="simple",
                success_criteria="Done",
                subtasks=[
                    SubTask(id="sub_1", description="Fail task", agent_key="HAKIM",
                            success_criteria="Fail", approval_required=False),
                ],
            )

            with patch("src.ai.agentic.coordinator.Worker.execute") as mock_worker:
                from src.ai.agentic.worker import SubTaskResult
                mock_worker.return_value = SubTaskResult(
                    agent_key="HAKIM", description="Fail", result="", status="failed", error="Boom",
                )

                flow = TaskExecutionFlowV2()
                response = flow.run(prompt="Test", model="gpt-4o-mini")

        assert response.status == "chat"
        assert "gagal" in (response.message or "").lower() or "failed" in (response.message or "").lower()

    def test_partial_success(self):
        """One success, one fail should return success with partial results."""
        with patch("src.ai.agentic.planner.Planner.plan") as mock_plan:
            from src.ai.agentic.plan import Plan, SubTask, ToolHint

            mock_plan.return_value = Plan(
                intent="Test",
                complexity="moderate",
                success_criteria="Done",
                subtasks=[
                    SubTask(id="sub_1", description="First", agent_key="HAKIM",
                            success_criteria="OK", approval_required=False),
                    SubTask(id="sub_2", description="Second", agent_key="MAYA",
                            success_criteria="OK", approval_required=False,
                            depends_on=["sub_1"]),
                ],
            )

            with patch("src.ai.agentic.coordinator.Worker.execute") as mock_worker:
                from src.ai.agentic.worker import SubTaskResult

                def side_effect(subtask, model, org_id=None):
                    return SubTaskResult(
                        agent_key=subtask.agent_key,
                        description=subtask.description,
                        result="ok" if subtask.id == "sub_1" else "",
                        status="success" if subtask.id == "sub_1" else "failed",
                        error=None if subtask.id == "sub_1" else "Error",
                    )

                mock_worker.side_effect = side_effect
                flow = TaskExecutionFlowV2()
                response = flow.run(prompt="Test", model="gpt-4o-mini")

        assert response.status == "success"
        assert len(response.results) == 2

    def test_empty_plan_returns_chat(self):
        """When the Planner returns an empty plan (no subtasks), V2 falls back."""
        with patch("src.ai.agentic.planner.Planner.plan") as mock_plan:
            from src.ai.agentic.plan import Plan

            mock_plan.return_value = Plan(
                intent="Nothing",
                complexity="simple",
                success_criteria="Nothing",
                subtasks=[],
            )

            flow = TaskExecutionFlowV2()
            response = flow.run(prompt="Halo", model="gpt-4o-mini")

        assert response.status == "chat"
