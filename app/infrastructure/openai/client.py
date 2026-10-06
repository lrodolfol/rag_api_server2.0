"""OpenAI async client factory.

Isolates construction of the third-party :class:`openai.AsyncOpenAI` client so
the rest of the service depends on an injected client instance, which keeps the
service unit-testable without touching the network.

A request timeout is always applied (never an unbounded external call) and the
API key is read from the typed configuration, never hardcoded or logged.
"""

from typing import Final

from openai import AsyncOpenAI

from app.infrastructure.config import OpenAIConfig

DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0


def create_openai_client(
    config: OpenAIConfig,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> AsyncOpenAI:
    """Build an :class:`AsyncOpenAI` client from the application configuration."""
    return AsyncOpenAI(
        api_key=config.api_key.get_secret_value(),
        timeout=timeout,
    )
