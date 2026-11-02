"""Unit tests for :class:`RedisAnswerCacheRepository` using an in-memory fake Redis."""

import logging
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import RedisError

from app.infrastructure.redis import (
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    RedisAnswerCacheRepository,
)

CACHE_KEY = "a" * 64
REDIS_KEY = f"{ANSWER_CACHE_KEY_PREFIX}:{CACHE_KEY}"
ANSWER = "Encontrei a Padaria Central"


@pytest.fixture
def client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.mark.asyncio
async def test_should_return_none_on_cache_miss(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    result = await repository.get(CACHE_KEY)

    # Assert
    assert result is None
    assert await client.exists(REDIS_KEY) == 0


@pytest.mark.asyncio
async def test_should_store_answer_with_prefix_and_ttl(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, ANSWER)

    # Assert
    assert await client.get(REDIS_KEY) == ANSWER
    assert 0 < await client.ttl(REDIS_KEY) <= ANSWER_CACHE_TTL_SECONDS


@pytest.mark.asyncio
async def test_should_return_answer_and_renew_ttl_on_hit(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set(CACHE_KEY, ANSWER)
    await client.expire(REDIS_KEY, 60)

    # Act
    result = await repository.get(CACHE_KEY)

    # Assert
    assert result == ANSWER
    assert await client.ttl(REDIS_KEY) > ANSWER_CACHE_TTL_SECONDS - 10


@pytest.mark.asyncio
async def test_should_treat_read_failure_as_miss(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    client = AsyncMock()
    client.getex.side_effect = RedisError("connection refused")
    repository = RedisAnswerCacheRepository(client)

    # Act
    with caplog.at_level(logging.ERROR):
        result = await repository.get(CACHE_KEY)

    # Assert
    assert result is None
    assert "Failed to read answer cache" in caplog.text


@pytest.mark.asyncio
async def test_should_not_raise_on_write_failure(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    client = AsyncMock()
    client.set.side_effect = RedisError("connection refused")
    repository = RedisAnswerCacheRepository(client)

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.set(CACHE_KEY, ANSWER)

    # Assert
    assert "Failed to write answer cache" in caplog.text


@pytest.mark.asyncio
async def test_should_not_log_answer_or_full_key(
    client: FakeAsyncRedis, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    with caplog.at_level(logging.INFO):
        await repository.set(CACHE_KEY, ANSWER)
        await repository.get(CACHE_KEY)

    # Assert
    assert ANSWER not in caplog.text
    assert CACHE_KEY not in caplog.text
    assert CACHE_KEY[:8] in caplog.text
