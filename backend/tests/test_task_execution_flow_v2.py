"""Tests for TaskExecutionFlowV2's cancellation handling
(src/ai/flows/task_execution_flow_v2.py)."""

from unittest.mock import patch

from src.ai.agentic.plan import Plan, SubTask
from src.ai.agentic.worker import SubTaskResult
from src.ai.flows.task_execution_flow_v2 import TaskExecutionFlowV2


def _plan_with_one_subtask():
    return Plan(
        intent="Test",
        complexity="simple",
        success_criteria="Done",
        subtasks=[
            SubTask(id="sub_1", description="Do it", agent_key="HAKIM", success_criteria="Done"),
        ],
    )


def test_returns_cancelled_response_when_stopped_before_coordinator_runs():
    plan = _plan_with_one_subtask()
    with patch("src.ai.flows.task_execution_flow_v2.Planner") as MockPlanner, \
         patch("src.ai.flows.task_execution_flow_v2.Coordinator") as MockCoordinator:
        MockPlanner.return_value.plan.return_value = plan

        flow = TaskExecutionFlowV2(should_stop=lambda: True)
        response = flow.run(prompt="test")

        assert response.status == "cancelled"
        MockCoordinator.assert_not_called()


def test_returns_cancelled_response_when_all_subtasks_end_up_cancelled():
    plan = _plan_with_one_subtask()
    cancelled_result = SubTaskResult(
        agent_key="HAKIM", description="Do it", result="", status="cancelled",
    )
    with patch("src.ai.flows.task_execution_flow_v2.Planner") as MockPlanner, \
         patch("src.ai.flows.task_execution_flow_v2.Coordinator") as MockCoordinator:
        MockPlanner.return_value.plan.return_value = plan
        MockCoordinator.return_value.execute.return_value = [cancelled_result]

        flow = TaskExecutionFlowV2()
        response = flow.run(prompt="test")

        assert response.status == "cancelled"


def test_should_stop_is_forwarded_to_coordinator():
    plan = _plan_with_one_subtask()
    should_stop = lambda: False
    with patch("src.ai.flows.task_execution_flow_v2.Planner") as MockPlanner, \
         patch("src.ai.flows.task_execution_flow_v2.Coordinator") as MockCoordinator:
        MockPlanner.return_value.plan.return_value = plan
        MockCoordinator.return_value.execute.return_value = [
            SubTaskResult(agent_key="HAKIM", description="Do it", result="OK", status="success"),
        ]

        flow = TaskExecutionFlowV2(should_stop=should_stop)
        flow.run(prompt="test")

        assert MockCoordinator.call_args.kwargs["should_stop"] is should_stop


def test_normal_success_response_unaffected_by_cancellation_plumbing():
    """Regression guard: adding should_stop must not change the happy path."""
    plan = _plan_with_one_subtask()
    with patch("src.ai.flows.task_execution_flow_v2.Planner") as MockPlanner, \
         patch("src.ai.flows.task_execution_flow_v2.Coordinator") as MockCoordinator:
        MockPlanner.return_value.plan.return_value = plan
        MockCoordinator.return_value.execute.return_value = [
            SubTaskResult(agent_key="HAKIM", description="Do it", result="Hasil", status="success"),
        ]

        flow = TaskExecutionFlowV2()
        response = flow.run(prompt="test")

        assert response.status == "success"
        assert response.results[0].result == "Hasil"
