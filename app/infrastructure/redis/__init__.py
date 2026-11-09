"""Redis integration package.

Exposes the async conversation-history and answer-cache repositories used by
the search flow, the categories catalog repository, the factory that builds the underlying async client from the
typed configuration, the per-channel key model, and the TTL/prefix constants.
"""

from app.infrastructure.redis.answer_cache_repository import (
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    RedisAnswerCacheRepository,
)
from app.infrastructure.redis.category_repository import RedisCategoryRepository
from app.infrastructure.redis.client import create_redis_client
from app.infrastructure.redis.models import HistoryChannel
from app.infrastructure.redis.repository import (
    HISTORY_TTL_SECONDS,
    RedisHistoryRepository,
)

__all__ = [
    "ANSWER_CACHE_KEY_PREFIX",
    "ANSWER_CACHE_TTL_SECONDS",
    "HISTORY_TTL_SECONDS",
    "HistoryChannel",
    "RedisAnswerCacheRepository",
    "RedisCategoryRepository",
    "RedisHistoryRepository",
    "create_redis_client",
]
