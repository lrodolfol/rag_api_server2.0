"""Asynchronous Redis repository for the knowledge-base categories catalog.

Category names live in a Redis SET (key from the configuration), so writes are
idempotent: seeding the initial list on every startup never duplicates nor
removes categories added later.

The catalog must never break registration, search or startup: read failures
are logged and treated as an empty catalog, write failures are logged and the
flow continues.
"""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.infrastructure.config import CategoriesConfig
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class RedisCategoryRepository:
    """Async repository for the category names kept in a Redis SET."""

    def __init__(self, client: Redis, config: CategoriesConfig) -> None:
        self._client = client
        self._key = config.redis_key

    async def get_all(self) -> list[str]:
        """Return every category name in alphabetical order (``[]`` on failure)."""
        try:
            names = await self._client.smembers(self._key)
        except RedisError:
            logger.exception("Failed to read the categories catalog")
            return []
        return sorted(names)

    async def add(self, name: str) -> None:
        """Add one category name to the catalog."""
        try:
            await self._client.sadd(self._key, name)
        except RedisError:
            logger.exception("Failed to add category '%s' to the catalog", name)

    async def seed(self, names: list[str]) -> None:
        """Add every name to the catalog in a single command."""
        if not names:
            return
        try:
            await self._client.sadd(self._key, *names)
        except RedisError:
            logger.exception("Failed to seed the categories catalog")
            return
        logger.info("Categories catalog seeded with %d initial categories", len(names))
