from src.ai.providers.base import LLMProvider
from src.ai.providers.errors import UnsupportedProviderError
from src.ai.providers.openai_provider import OpenAIProvider
from src.core.config import OPENAI_API_KEY


# Lazy imports inside resolve_provider() so optional SDKs (anthropic,
# google-genai) are not required at import time. See provider subclasses
# for the `pip install` instructions.


def _get_env(env_var: str, default: str = "") -> str:
    import os
    return os.getenv(env_var, default)


def get_openai_key(org_id: str | None = None) -> str:
    """Platform-wide key for MVP. `org_id` is accepted now so a future per-org
    BYO-key (Phase 4, see docs/architecture/ai-execution-crewai.md §4.2) becomes a
    change inside this function only — no call-site changes anywhere else."""
    return OPENAI_API_KEY


def resolve_provider(provider_name: str, org_id: str | None = None) -> LLMProvider:
    """Resolve an `agents.provider` value to a concrete LLMProvider instance.

    Supported provider values (case-insensitive):
    - `openai`     — OpenAI (MVP default, requires OPENAI_API_KEY).
    - `anthropic`  — Anthropic Claude (requires `anthropic` package + ANTHROPIC_API_KEY).
    - `gemini`     — Google Gemini (requires `google-genai` + GEMINI_API_KEY / GOOGLE_API_KEY).
    - `openrouter` — OpenRouter (requires OPENROUTER_API_KEY).
    - `ollama`     — Local Ollama (no key; set OLLAMA_BASE_URL if not on localhost).
    - `azure`      — Azure OpenAI (requires AZURE_OPENAI_API_KEY + AZURE_OPENAI_BASE_URL).
    """
    name = (provider_name or "").lower()

    if name == "openai":
        return OpenAIProvider(api_key=get_openai_key(org_id))

    if name == "anthropic":
        from src.ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=_get_env("ANTHROPIC_API_KEY"))

    if name in ("gemini", "google", "google_gemini"):
        from src.ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=_get_env("GEMINI_API_KEY") or _get_env("GOOGLE_API_KEY")
        )

    if name == "openrouter":
        from src.ai.providers.openai_compat_providers import OpenRouterProvider
        return OpenRouterProvider(api_key=_get_env("OPENROUTER_API_KEY"))

    if name == "ollama":
        from src.ai.providers.openai_compat_providers import OllamaProvider
        return OllamaProvider(
            api_key=_get_env("OLLAMA_API_KEY", "ollama"),
            base_url=_get_env("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )

    if name in ("azure", "azure_openai"):
        from src.ai.providers.openai_compat_providers import AzureOpenAIProvider
        return AzureOpenAIProvider(
            api_key=_get_env("AZURE_OPENAI_API_KEY"),
            base_url=_get_env("AZURE_OPENAI_BASE_URL"),
        )

    raise UnsupportedProviderError(provider_name)
