"""Integration tests for the Redis answer cache with a fake Redis server.

``fakeredis`` provides an in-memory, protocol-accurate async server so the
expiry of a stored answer and the category index (write, invalidation and the
removal of the index members) are exercised end to end through the repository;
the write and sliding TTL renewal details are covered by the unit tests.
"""

import asyncio

import pytest
from fakeredis import FakeAsyncRedis

from app.infrastructure.redis import (
    ANSWER_CACHE_CATEGORY_PREFIX,
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    UNCATEGORIZED_SLUG,
    RedisAnswerCacheRepository,
)

CACHE_KEY = "b" * 64
REDIS_KEY = f"{ANSWER_CACHE_KEY_PREFIX}:{CACHE_KEY}"
FOOD_KEY = "f" * 64
BEAUTY_KEY = "e" * 64
UNCATEGORIZED_KEY = "c" * 64
FOOD_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:alimentacao"
BEAUTY_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:beleza"
UNCATEGORIZED_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:{UNCATEGORIZED_SLUG}"


@pytest.fixture
def client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


async def _seeded_repository(client: FakeAsyncRedis) -> RedisAnswerCacheRepository:
    """Repository with one answer in ``alimentacao``, one in ``beleza`` and one uncategorized."""
    repository = RedisAnswerCacheRepository(client)
    await repository.set(FOOD_KEY, "Padaria Central", {"alimentacao"})
    await repository.set(BEAUTY_KEY, "Salão Bela", {"beleza"})
    await repository.set(UNCATEGORIZED_KEY, "Padaria e Salão", {None})
    return repository


@pytest.mark.asyncio
async def test_should_miss_after_key_expires(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set(CACHE_KEY, "Padaria Central", {"alimentacao"})
    await client.pexpire(REDIS_KEY, 1)
    await asyncio.sleep(0.05)

    # Act
    result = await repository.get(CACHE_KEY)

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_should_store_answer_with_ttl_and_category_set_without_ttl(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, "Padaria Central", {"alimentacao"})

    # Assert
    assert 0 < await client.ttl(REDIS_KEY) <= ANSWER_CACHE_TTL_SECONDS
    assert await client.sismember(FOOD_SET, CACHE_KEY)
    assert await client.ttl(FOOD_SET) == -1


@pytest.mark.asyncio
async def test_should_index_answer_in_every_category_including_uncategorized(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, "Padaria Central", {"alimentacao", "beleza", None})

    # Assert
    assert await client.sismember(FOOD_SET, CACHE_KEY)
    assert await client.sismember(BEAUTY_SET, CACHE_KEY)
    assert await client.sismember(UNCATEGORIZED_SET, CACHE_KEY)


@pytest.mark.asyncio
async def test_should_invalidate_category_and_uncategorized_answers_only(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    seeded_repository = await _seeded_repository(client)

    # Act
    await seeded_repository.invalidate_category("alimentacao")

    # Assert
    assert await seeded_repository.get(FOOD_KEY) is None
    assert await seeded_repository.get(UNCATEGORIZED_KEY) is None
    assert await seeded_repository.get(BEAUTY_KEY) == "Salão Bela"
    assert await client.exists(FOOD_SET, UNCATEGORIZED_SET) == 0
    assert await client.smembers(BEAUTY_SET) == {BEAUTY_KEY}


@pytest.mark.asyncio
async def test_should_invalidate_only_uncategorized_answers_for_none(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    seeded_repository = await _seeded_repository(client)

    # Act
    await seeded_repository.invalidate_category(None)

    # Assert
    assert await seeded_repository.get(UNCATEGORIZED_KEY) is None
    assert await seeded_repository.get(FOOD_KEY) == "Padaria Central"
    assert await seeded_repository.get(BEAUTY_KEY) == "Salão Bela"
    assert await client.smembers(FOOD_SET) == {FOOD_KEY}


@pytest.mark.asyncio
async def test_should_remove_index_member_of_already_expired_answer(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set(CACHE_KEY, "Padaria Central", {"alimentacao"})
    await client.delete(REDIS_KEY)

    # Act
    await repository.invalidate_category("alimentacao")

    # Assert
    assert await client.exists(FOOD_SET) == 0


@pytest.mark.asyncio
async def test_should_not_fail_when_invalidating_category_without_answers(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.invalidate_category("alimentacao")

    # Assert
    assert await client.dbsize() == 0


@pytest.mark.asyncio
async def test_should_index_answer_again_after_invalidation(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    seeded_repository = await _seeded_repository(client)
    await seeded_repository.invalidate_category("alimentacao")

    # Act
    await seeded_repository.set(FOOD_KEY, "Padaria Nova", {"alimentacao"})

    # Assert
    assert await seeded_repository.get(FOOD_KEY) == "Padaria Nova"
    assert await client.smembers(FOOD_SET) == {FOOD_KEY}
