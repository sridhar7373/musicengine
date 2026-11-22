"""Provider selection based on the URL supplied to the CLI."""

from urllib.parse import urlparse

from .base import BaseProvider
from .isaimini import IsaiminiProvider


PROVIDER_TYPES: tuple[type[BaseProvider], ...] = (IsaiminiProvider,)
DEFAULT_PROVIDER = IsaiminiProvider


def default_provider() -> BaseProvider:
    return DEFAULT_PROVIDER()


def provider_for_url(url: str) -> BaseProvider:
    for provider_type in PROVIDER_TYPES:
        if provider_type.supports(url):
            return provider_type()
    raise ValueError(f"No provider supports this URL: {url}")


def provider_for_artist_input(value: str, delay: float = 1.0) -> tuple[BaseProvider, str]:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return provider_for_url(value), value
    provider = default_provider()
    return provider, provider.resolve_artist_url(value, delay=delay)
