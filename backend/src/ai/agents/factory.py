from crewai import Agent

from src.ai.agents.registry import AgentConfig
from src.ai.agents.tool_mappings import get_all_tools_for_agent
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter, ResultCallback
from src.ai.providers.registry import resolve_provider


def build_crewai_agent(
    config: AgentConfig,
    llm: InfinityLLMAdapter | None = None,
    on_result: ResultCallback | None = None,
) -> Agent:
    """Assemble a crewai.Agent from an AgentConfig. This is the only place that
    turns 'an agent persona exists' into 'CrewAI can execute it' — see
    docs/architecture/ai-execution-crewai.md §5.1. No prompt content is authored
    here, only assembly.

    Tools are automatically attached per `tool_mappings.py` — no call-site
    needs to pass them. Adding/removing a tool for an agent is a one-line
    change in that single mapping file.

    `llm` can be pre-built and passed in (e.g. to share one adapter/callback across
    a batch); if omitted, one is built from `config.provider`/`config.model` via the
    AI Provider Interface.

    `allow_delegation=False` on every agent, including Claudia — delegation is our
    Flow's routing step (§3.2/§5.1), never CrewAI's own manager-agent delegation.
    """
    if llm is None:
        provider = resolve_provider(config.provider, config.org_id)
        llm = InfinityLLMAdapter(
            provider=provider,
            model=config.model,
            agent_key=config.key,
            org_id=config.org_id,
            on_result=on_result,
        )

    return Agent(
        role=config.role,
        goal=config.goal,
        backstory=config.backstory,
        llm=llm,
        tools=get_all_tools_for_agent(config.key),
        allow_delegation=False,
        verbose=False,
    )
