"""Tests for Worker (src/ai/agentic/worker.py)."""

from unittest.mock import patch

import pytest

from src.ai.agentic.plan import SubTask
from src.ai.agentic.worker import SubTaskResult, Worker


class TestSubTaskResult:
    def test_default_status(self):
        r = SubTaskResult(agent_key="HAKIM", description="X", result="ok")
        assert r.status == "success"
        assert r.artifacts == []
        assert r.speed == "0s"
        assert r.error is None
        assert r.tool_call_count == 0

    def test_skipped_status(self):
        r = SubTaskResult(agent_key="MAYA", description="X", result="", status="skipped")
        assert r.status == "skipped"

    def test_with_error(self):
        r = SubTaskResult(agent_key="NEXUS", description="X", result="", status="failed", error="Something broke")
        assert r.status == "failed"
        assert r.error == "Something broke"


class TestWorker:
    def test_unknown_agent(self):
        """Worker should return SubTaskResult with status='failed' when the
        agent is not found in the registry."""
        worker = Worker()
        subtask = SubTask(
            id="sub_1",
            description="Do something",
            agent_key="NONEXISTENT",
            success_criteria="Finish it",
        )
        result = worker.execute(subtask, model="gpt-4o-mini")
        assert result.status == "failed"
        assert result.error is not None
        assert "NONEXISTENT" in result.error

    def test_on_event_called(self):
        """Worker calls on_event for subtask_start and subtask_done."""
        events = []

        worker = Worker(on_event=lambda t, p: events.append((t, p)))
        subtask = SubTask(
            id="sub_1",
            description="Do test",
            agent_key="NONEXISTENT",
            success_criteria="Done",
        )
        worker.execute(subtask, model="gpt-4o-mini")

        event_types = [e[0] for e in events]
        assert "subtask_start" in event_types
        assert "subtask_done" in event_types

    def test_empty_description(self):
        """Worker can handle an empty description."""
        worker = Worker()
        subtask = SubTask(
            id="sub_1",
            description="",
            agent_key="NONEXISTENT",
            success_criteria="",
        )
        result = worker.execute(subtask, model="gpt-4o-mini")
        assert result.status == "failed"


class TestWorkerCancellation:
    def test_should_stop_true_before_start_returns_cancelled_without_events(self):
        """If the run was already cancelled before this subtask even got
        picked up, the Worker shouldn't start it (no subtask_start/done —
        there's nothing to show in the timeline for work that never ran)."""
        events = []
        worker = Worker(on_event=lambda t, p: events.append((t, p)), should_stop=lambda: True)
        subtask = SubTask(id="sub_1", description="Do something", agent_key="HAKIM", success_criteria="Done")

        result = worker.execute(subtask, model="gpt-4o-mini")

        assert result.status == "cancelled"
        assert events == []

    def test_is_cancellation_recognizes_wrapped_interrupted_error(self):
        from src.ai.agentic.worker import _is_cancellation

        try:
            try:
                raise InterruptedError("stopped mid-stream")
            except InterruptedError as inner:
                raise RuntimeError("CrewAI wrapped it") from inner
        except RuntimeError as wrapped:
            assert _is_cancellation(wrapped) is True

    def test_is_cancellation_false_for_unrelated_error(self):
        from src.ai.agentic.worker import _is_cancellation

        assert _is_cancellation(RuntimeError("just a normal failure")) is False
