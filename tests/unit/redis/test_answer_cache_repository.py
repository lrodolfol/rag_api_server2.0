"""Unit tests for :class:`RedisAnswerCacheRepository` using an in-memory fake Redis."""

import logging
from types import TracebackType
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import RedisError

from app.infrastructure.redis import (
    ANSWER_CACHE_CATEGORY_PREFIX,
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    UNCATEGORIZED_SLUG,
    RedisAnswerCacheRepository,
)

CACHE_KEY = "a" * 64
REDIS_KEY = f"{ANSWER_CACHE_KEY_PREFIX}:{CACHE_KEY}"
ANSWER = "Encontrei a Padaria Central"
FOOD_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:alimentacao"
BEAUTY_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:beleza"
UNCATEGORIZED_SET = f"{ANSWER_CACHE_CATEGORY_PREFIX}:{UNCATEGORIZED_SLUG}"


class _FailingPipeline:
    """Pipeline stand-in whose ``execute`` fails like an unreachable Redis."""

    async def __aenter__(self) -> "_FailingPipeline":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def __getattr__(self, name: str) -> MagicMock:
        return MagicMock(return_value=self)

    async def execute(self) -> list[int]:
        raise RedisError("connection refused")


def _failing_pipeline_client() -> MagicMock:
    client = MagicMock()
    client.pipeline.return_value = _FailingPipeline()
    client.smembers = AsyncMock(return_value={CACHE_KEY})
    return client


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
    await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})

    # Assert
    assert await client.get(REDIS_KEY) == ANSWER
    assert 0 < await client.ttl(REDIS_KEY) <= ANSWER_CACHE_TTL_SECONDS


@pytest.mark.asyncio
async def test_should_return_answer_and_renew_ttl_on_hit(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})
    await client.expire(REDIS_KEY, 60)

    # Act
    result = await repository.get(CACHE_KEY)

    # Assert
    assert result == ANSWER
    assert await client.ttl(REDIS_KEY) > ANSWER_CACHE_TTL_SECONDS - 10


@pytest.mark.asyncio
async def test_should_write_answer_and_index_in_a_transaction(client: FakeAsyncRedis) -> None:
    # Arrange
    pipeline_spy = MagicMock(wraps=client.pipeline)
    client.pipeline = pipeline_spy
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})

    # Assert
    pipeline_spy.assert_called_once_with(transaction=True)


@pytest.mark.asyncio
async def test_should_index_answer_in_each_category_set(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, ANSWER, {"alimentacao", "beleza"})

    # Assert
    assert await client.smembers(FOOD_SET) == {CACHE_KEY}
    assert await client.smembers(BEAUTY_SET) == {CACHE_KEY}
    assert await client.exists(UNCATEGORIZED_SET) == 0


@pytest.mark.asyncio
async def test_should_index_uncategorized_answer_in_none_set(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, ANSWER, {None})

    # Assert
    assert await client.smembers(UNCATEGORIZED_SET) == {CACHE_KEY}


@pytest.mark.asyncio
async def test_should_not_set_ttl_on_category_set(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})

    # Assert
    assert await client.ttl(FOOD_SET) == -1


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
    repository = RedisAnswerCacheRepository(_failing_pipeline_client())

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})

    # Assert
    assert "Failed to write answer cache" in caplog.text


@pytest.mark.asyncio
async def test_should_invalidate_category_and_uncategorized_answers(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set("food", ANSWER, {"alimentacao"})
    await repository.set("beauty", ANSWER, {"beleza"})
    await repository.set("none", ANSWER, {None})

    # Act
    await repository.invalidate_category("alimentacao")

    # Assert
    assert await client.exists(f"{ANSWER_CACHE_KEY_PREFIX}:food") == 0
    assert await client.exists(f"{ANSWER_CACHE_KEY_PREFIX}:none") == 0
    assert await client.get(f"{ANSWER_CACHE_KEY_PREFIX}:beauty") == ANSWER
    assert await client.smembers(BEAUTY_SET) == {"beauty"}


@pytest.mark.asyncio
async def test_should_invalidate_only_uncategorized_answers_for_none(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set("food", ANSWER, {"alimentacao"})
    await repository.set("none", ANSWER, {None})

    # Act
    await repository.invalidate_category(None)

    # Assert
    assert await client.exists(f"{ANSWER_CACHE_KEY_PREFIX}:none") == 0
    assert await client.get(f"{ANSWER_CACHE_KEY_PREFIX}:food") == ANSWER


@pytest.mark.asyncio
@pytest.mark.parametrize("blank_slug", ["", "   "])
async def test_should_reject_blank_category_slug(
    client: FakeAsyncRedis, blank_slug: str
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act / Assert
    with pytest.raises(ValueError):
        await repository.invalidate_category(blank_slug)


@pytest.mark.asyncio
async def test_should_not_delete_anything_when_category_set_is_empty(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    pipeline_spy = MagicMock(wraps=client.pipeline)
    client.pipeline = pipeline_spy
    repository = RedisAnswerCacheRepository(client)

    # Act
    await repository.invalidate_category("alimentacao")

    # Assert
    pipeline_spy.assert_not_called()


@pytest.mark.asyncio
async def test_should_not_raise_when_reading_category_set_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    client = MagicMock()
    client.smembers = AsyncMock(side_effect=RedisError("connection refused"))
    repository = RedisAnswerCacheRepository(client)

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.invalidate_category("alimentacao")

    # Assert
    assert "Failed to invalidate answer cache (category='alimentacao')" in caplog.text


@pytest.mark.asyncio
async def test_should_not_raise_when_deleting_answers_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(_failing_pipeline_client())

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.invalidate_category("alimentacao")

    # Assert
    assert "Failed to invalidate answer cache (category='alimentacao')" in caplog.text


@pytest.mark.asyncio
async def test_should_log_category_and_deleted_count_on_invalidation(
    client: FakeAsyncRedis, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)
    await repository.set("food", ANSWER, {"alimentacao"})
    await repository.set("none", ANSWER, {None})

    # Act
    with caplog.at_level(logging.INFO):
        await repository.invalidate_category("alimentacao")

    # Assert
    assert "Answer cache invalidated (category='alimentacao', keys=2)" in caplog.text


@pytest.mark.asyncio
async def test_should_not_log_answer_or_full_key(
    client: FakeAsyncRedis, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    repository = RedisAnswerCacheRepository(client)

    # Act
    with caplog.at_level(logging.INFO):
        await repository.set(CACHE_KEY, ANSWER, {"alimentacao"})
        await repository.get(CACHE_KEY)
        await repository.invalidate_category("alimentacao")

    # Assert
    assert ANSWER not in caplog.text
    assert CACHE_KEY not in caplog.text
    assert CACHE_KEY[:8] in caplog.text
