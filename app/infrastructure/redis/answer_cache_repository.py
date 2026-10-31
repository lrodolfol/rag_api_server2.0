"""Asynchronous Redis answer-cache repository.

Stores generated answers keyed by the question fingerprint hash. Every key is
written with a 24-hour TTL that is renewed on each cache hit (sliding TTL): keys
queried at least once a day never expire, rarely used keys expire on their own.

The cache is an optimisation, never a dependency of the search flow: Redis
failures are logged and treated as a miss (read) or ignored (write). Neither
questions nor answers are logged; only a short prefix of the key hash is.
"""

from typing import Final

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

ANSWER_CACHE_TTL_SECONDS: Final[int] = 24 * 60 * 60
ANSWER_CACHE_KEY_PREFIX: Final[str] = "rag_answer_cache"
_LOGGED_KEY_LENGTH: Final[int] = 8


class RedisAnswerCacheRepository:
    """Async repository for cached RAG answers kept in Redis."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, cache_key: str) -> str | None:
        """Return the cached answer and renew its TTL, or ``None`` on miss/failure."""
        try:
            answer = await self._client.getex(
                self._key(cache_key), ex=ANSWER_CACHE_TTL_SECONDS
            )
        except RedisError:
            logger.exception("Failed to read answer cache (key='%s')", _short(cache_key))
            return None
        if answer is None:
            logger.info("Answer cache miss (key='%s')", _short(cache_key))
            return None
        logger.info("Answer cache hit, TTL renewed (key='%s')", _short(cache_key))
        return answer

    async def set(self, cache_key: str, answer: str) -> None:
        """Store ``answer`` under ``cache_key`` with the 24-hour TTL."""
        try:
            await self._client.set(
                self._key(cache_key), answer, ex=ANSWER_CACHE_TTL_SECONDS
            )
        except RedisError:
            logger.exception("Failed to write answer cache (key='%s')", _short(cache_key))
            return
        logger.info("Answer stored in cache (key='%s')", _short(cache_key))

    @staticmethod
    def _key(cache_key: str) -> str:
        return f"{ANSWER_CACHE_KEY_PREFIX}:{cache_key}"


def _short(cache_key: str) -> str:
    return cache_key[:_LOGGED_KEY_LENGTH]
