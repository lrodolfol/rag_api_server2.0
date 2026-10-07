"""Redis integration package.

Exposes the async conversation-history repository used by the search flow, the
factory that builds the underlying async client from the typed configuration,
the per-channel key model, and the history TTL constant.
"""

from app.infrastructure.redis.client import create_redis_client
from app.infrastructure.redis.models import HistoryChannel
from app.infrastructure.redis.repository import (
    HISTORY_TTL_SECONDS,
    RedisHistoryRepository,
)

__all__ = [
    "HISTORY_TTL_SECONDS",
    "HistoryChannel",
    "RedisHistoryRepository",
    "create_redis_client",
]
