"""Asynchronous Redis conversation-history repository.

Stores each user's message history as a Redis list, namespaced by channel so the
WhatsApp and online-chat histories never collide. Every append refreshes a
30-minute sliding TTL, matching the product requirement that history expires
after 30 minutes of inactivity.

The :class:`redis.asyncio.Redis` client is injected (never built here) to keep
the repository unit-testable. Redis failures are translated into the domain
:class:`HistoryStoreError`; user codes are never logged.
"""

import json
from typing import Final

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain import HistoryStoreError, MessageHistoryItem
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis.models import HistoryChannel

logger = get_logger(__name__)

HISTORY_TTL_SECONDS: Final[int] = 30 * 60


class RedisHistoryRepository:
    """Async repository for per-user conversation history kept in Redis."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get_history(
        self, channel: HistoryChannel, user_code: str
    ) -> list[MessageHistoryItem]:
        """Return the stored message history for a user on a given channel."""
        key = self._key(channel, user_code)
        try:
            raw_items = await self._client.lrange(key, 0, -1)
        except RedisError as error:
            logger.exception("Failed to read conversation history from Redis")
            raise HistoryStoreError("Failed to read conversation history") from error
        return [self._deserialize(item) for item in raw_items]

    async def append_message(
        self,
        channel: HistoryChannel,
        user_code: str,
        message: MessageHistoryItem,
    ) -> None:
        """Append a message and refresh the 30-minute sliding TTL."""
        key = self._key(channel, user_code)
        try:
            await self._client.rpush(key, self._serialize(message))
            await self._client.expire(key, HISTORY_TTL_SECONDS)
        except RedisError as error:
            logger.exception("Failed to append conversation history to Redis")
            raise HistoryStoreError("Failed to append conversation history") from error

    @staticmethod
    def _key(channel: HistoryChannel, user_code: str) -> str:
        return f"{channel.value}:{user_code}"

    @staticmethod
    def _serialize(message: MessageHistoryItem) -> str:
        return message.model_dump_json()

    @staticmethod
    def _deserialize(raw_item: str | bytes) -> MessageHistoryItem:
        payload = raw_item.decode("utf-8") if isinstance(raw_item, bytes) else raw_item
        return MessageHistoryItem(**json.loads(payload))
