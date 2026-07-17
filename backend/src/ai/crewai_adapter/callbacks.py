from src.ai.crewai_adapter.llm_adapter import ResultCallback
from src.ai.providers.base import LLMResult
from src.core.config import logger


def structured_log_callback(agent_key: str, org_id: str | None, result: LLMResult) -> None:
    """Default `on_result` callback for InfinityLLMAdapter — structured log only.

    Step 5 (TaskExecutionFlow) chains this with a DB-persisting callback (writing
    `agent_runs`, see docs/architecture/ai-execution-crewai.md §7.2) once the DB
    client exists. This function stays log-only so it's usable standalone before
    that lands, and stays useful afterward for local/dev visibility.
    """
    logger.info(
        "agent_run",
        extra={
            "org_id": org_id,
            "agent_key": agent_key,
            "provider": result["provider"],
            "model": result["model"],
            "tokens_in": result["tokens_in"],
            "tokens_out": result["tokens_out"],
            "cost_usd": result["cost_usd"],
            "duration_ms": result["duration_ms"],
        },
    )
    try:
        from src.services.logging import add_json_log
        agent_name = agent_key.capitalize()
        duration_sec = (result.get("duration_ms") or 0.0) / 1000.0
        add_json_log(
            agent=agent_name,
            model=result.get("model", "unknown"),
            status="Success",
            duration=duration_sec
        )
    except Exception:
        logger.exception("Failed to write daily activity JSON log")


def chain(*callbacks: ResultCallback) -> ResultCallback:
    """Combine several `on_result` callbacks into one, e.g. `chain(structured_log_callback,
    persist_agent_run)`. Each runs independently — one failing doesn't stop the rest,
    since a logging/audit failure should never take down agent execution."""

    def _combined(agent_key: str, org_id: str | None, result: LLMResult) -> None:
        for cb in callbacks:
            try:
                cb(agent_key, org_id, result)
            except Exception:
                logger.exception(f"on_result callback '{cb.__name__}' failed for agent '{agent_key}'")

    return _combined
