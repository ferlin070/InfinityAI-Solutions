class ProviderError(Exception):
    """Base class for all provider errors.

    Concrete providers catch their vendor SDK's native exceptions and re-raise one of
    these. Nothing above `src/ai/providers/` should ever see a vendor-specific
    exception type — this is what makes swapping providers safe.
    """


class ProviderAuthError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderContextLengthError(ProviderError):
    pass


class UnsupportedProviderError(ProviderError):
    def __init__(self, provider_name: str):
        super().__init__(f"Provider '{provider_name}' is not supported.")
        self.provider_name = provider_name
