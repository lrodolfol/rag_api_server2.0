"""Integration tests for the Redis answer cache with a fake Redis server.

``fakeredis`` provides an in-memory, protocol-accurate async server so the
expiry of a stored answer is exercised end to end through the repository; the
write and sliding TTL renewal are covered by the unit tests.
"""

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from app.infrastructure.redis import (
    ANSWER_CACHE_KEY_PREFIX,
    RedisAnswerCacheRepository,
)

CACHE_KEY = "b" * 64
REDIS_KEY = f"{ANSWER_CACHE_KEY_PREFIX}:{CACHE_KEY}"


@pytest.fixture
def client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_should_miss_after_key_expires(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set(CACHE_KEY, "Padaria Central")
    await client.pexpire(REDIS_KEY, 1)
    await asyncio.sleep(0.05)

    # Act
    result = await repository.get(CACHE_KEY)

    # Assert
    assert result is None
