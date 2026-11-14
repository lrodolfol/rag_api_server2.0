"""Asynchronous Redis answer-cache repository.

Stores generated answers keyed by the question fingerprint hash. Every key is
written with a 24-hour TTL that is renewed on each cache hit (sliding TTL): keys
queried at least once a day never expire, rarely used keys expire on their own.

Each answer is also indexed in one Redis SET per category of the answer
(``rag_answer_cache:category:<slug>``), whose members are the fingerprint
hashes, so the answers of a category can be invalidated when one of its
services changes. Answers without a category (search without a category
filter) go to the ``__none__`` SET: they may hold services of any category, so
that SET is invalidated together with every category. The SETs have no TTL on
purpose: the answer TTL is renewed on every hit, and a SET expiring before its
live answers would leave them out of the index forever. Members whose answers
already expired stay in the SET until the next invalidation of the category
(deleting a missing key is harmless).

The cache is an optimisation, never a dependency of the search flow: Redis
failures are logged and treated as a miss (read) or ignored (write and
invalidation). Neither questions nor answers are logged; only a short prefix of
the key hash is.
"""

from typing import Final

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

ANSWER_CACHE_TTL_SECONDS: Final[int] = 24 * 60 * 60
ANSWER_CACHE_KEY_PREFIX: Final[str] = "rag_answer_cache"
ANSWER_CACHE_CATEGORY_PREFIX: Final[str] = f"{ANSWER_CACHE_KEY_PREFIX}:category"
UNCATEGORIZED_SLUG: Final[str] = "__none__"
_LOGGED_KEY_LENGTH: Final[int] = 8


class RedisAnswerCacheRepository:
    """Async repository for cached RAG answers kept in Redis, indexed by category."""

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

    async def set(
        self, cache_key: str, answer: str, category_slugs: set[str | None]
    ) -> None:
        """Store ``answer`` with the 24-hour TTL and index it in each category SET.

        ``None`` in ``category_slugs`` indexes the answer as uncategorized. The
        answer and its index entries are written in a single transaction.
        """
        try:
            async with self._client.pipeline(transaction=True) as pipeline:
                pipeline.set(self._key(cache_key), answer, ex=ANSWER_CACHE_TTL_SECONDS)
                for category_slug in category_slugs:
                    pipeline.sadd(self._category_key(category_slug), cache_key)
                await pipeline.execute()
        except RedisError:
            logger.exception("Failed to write answer cache (key='%s')", _short(cache_key))
            return
        logger.info("Answer stored in cache (key='%s')", _short(cache_key))

    async def invalidate_category(self, category_slug: str | None) -> None:
        """Delete the answers of ``category_slug`` and the uncategorized ones.

        With ``None`` only the uncategorized answers are deleted. A blank slug
        is a caller bug (it would silently behave like a missing category) and
        raises ``ValueError``. Redis failures are logged and never raised.
        """
        if category_slug is not None and not category_slug.strip():
            raise ValueError("Category slug must not be blank")
        logged_category = category_slug or UNCATEGORIZED_SLUG
        slugs = [None] if category_slug is None else [category_slug, None]
        try:
            deleted = 0
            for slug in slugs:
                deleted += await self._invalidate_set(self._category_key(slug))
        except RedisError:
            logger.exception(
                "Failed to invalidate answer cache (category='%s')", logged_category
            )
            return
        logger.info(
            "Answer cache invalidated (category='%s', keys=%d)", logged_category, deleted
        )

    async def _invalidate_set(self, set_key: str) -> int:
        """Delete the answers indexed in ``set_key``; return how many were deleted.

        Only the members read are removed from the SET (never the whole SET), so
        an answer indexed concurrently, between the read and the removal, keeps
        its index entry.
        """
        cache_keys: set[str] = await self._client.smembers(set_key)
        if not cache_keys:
            return 0
        async with self._client.pipeline(transaction=True) as pipeline:
            pipeline.delete(*(self._key(cache_key) for cache_key in cache_keys))
            pipeline.srem(set_key, *cache_keys)
            deleted, _ = await pipeline.execute()
        return int(deleted)

    @staticmethod
    def _key(cache_key: str) -> str:
        return f"{ANSWER_CACHE_KEY_PREFIX}:{cache_key}"

    @staticmethod
    def _category_key(category_slug: str | None) -> str:
        slug = UNCATEGORIZED_SLUG if category_slug is None else category_slug
        return f"{ANSWER_CACHE_CATEGORY_PREFIX}:{slug}"


def _short(cache_key: str) -> str:
    return cache_key[:_LOGGED_KEY_LENGTH]
