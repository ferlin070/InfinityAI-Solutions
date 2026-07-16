from src.ai.providers.base import LLMProvider
from src.ai.providers.errors import UnsupportedProviderError
from src.ai.providers.openai_provider import OpenAIProvider
from src.core.config import OPENAI_API_KEY


def get_openai_key(org_id: str | None = None) -> str:
    """Platform-wide key for MVP. `org_id` is accepted now so a future per-org
    BYO-key (Phase 4, see docs/architecture/ai-execution-crewai.md §4.2) becomes a
    change inside this function only — no call-site changes anywhere else."""
    return OPENAI_API_KEY


def resolve_provider(provider_name: str, org_id: str | None = None) -> LLMProvider:
    """Resolve an `agents.provider` value to a concrete LLMProvider instance.

    MVP supports only 'openai' — everything else fails loudly rather than silently
    falling back, since a silent fallback would mean an agent running on the wrong
    provider/cost profile without anyone noticing.
    """
    if provider_name == "openai":
        return OpenAIProvider(api_key=get_openai_key(org_id))
    raise UnsupportedProviderError(provider_name)
