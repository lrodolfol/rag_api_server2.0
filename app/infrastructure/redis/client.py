"""Redis client factory.

Isolates construction of the asynchronous :class:`redis.asyncio.Redis` client so
the history repository depends on an injected client instance, keeping it
unit-testable (e.g. with ``fakeredis``) without touching a real server.

The password is read from the typed configuration, never hardcoded or logged.
Responses are decoded to ``str`` so the repository works with text payloads.
"""

from redis.asyncio import Redis

from app.infrastructure.config import RedisConfig


def create_redis_client(config: RedisConfig) -> Redis:
    """Build an async :class:`Redis` client from the application configuration."""
    return Redis(
        host=config.host,
        port=config.port,
        db=config.db,
        password=config.password.get_secret_value(),
        decode_responses=True,
    )
