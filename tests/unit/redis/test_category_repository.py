"""Unit tests for :class:`RedisCategoryRepository` with a mocked Redis client."""

import logging
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError

from app.infrastructure.config import CategoriesConfig
from app.infrastructure.redis import RedisCategoryRepository

REDIS_KEY = "knowledge_categories"
CONFIG = CategoriesConfig(redis_key=REDIS_KEY, initial=["SAÚDE", "BELEZA"], fallback="OUTROS")


@pytest.fixture
def client() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_should_return_names_in_alphabetical_order(client: AsyncMock) -> None:
    # Arrange
    client.smembers.return_value = {"SAÚDE", "ALIMENTAÇÃO", "BELEZA"}
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    names = await repository.get_all()

    # Assert
    assert names == ["ALIMENTAÇÃO", "BELEZA", "SAÚDE"]
    client.smembers.assert_awaited_once_with(REDIS_KEY)


@pytest.mark.asyncio
async def test_should_return_empty_list_and_log_on_read_failure(
    client: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    client.smembers.side_effect = RedisError("connection refused")
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    with caplog.at_level(logging.ERROR):
        names = await repository.get_all()

    # Assert
    assert names == []
    assert "Failed to read the categories catalog" in caplog.text


@pytest.mark.asyncio
async def test_should_add_one_name_to_the_set(client: AsyncMock) -> None:
    # Arrange
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    await repository.add("PETSHOP")

    # Assert
    client.sadd.assert_awaited_once_with(REDIS_KEY, "PETSHOP")


@pytest.mark.asyncio
async def test_should_log_and_continue_on_add_failure(
    client: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    client.sadd.side_effect = RedisError("connection refused")
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.add("PETSHOP")

    # Assert
    assert "Failed to add category 'PETSHOP'" in caplog.text


@pytest.mark.asyncio
async def test_should_seed_every_name_in_a_single_command(client: AsyncMock) -> None:
    # Arrange
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    await repository.seed(["SAÚDE", "BELEZA"])

    # Assert
    client.sadd.assert_awaited_once_with(REDIS_KEY, "SAÚDE", "BELEZA")


@pytest.mark.asyncio
async def test_should_not_call_redis_when_seeding_nothing(client: AsyncMock) -> None:
    # Arrange
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    await repository.seed([])

    # Assert
    client.sadd.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_log_and_continue_on_seed_failure(
    client: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    client.sadd.side_effect = RedisError("connection refused")
    repository = RedisCategoryRepository(client, CONFIG)

    # Act
    with caplog.at_level(logging.ERROR):
        await repository.seed(["SAÚDE"])

    # Assert
    assert "Failed to seed the categories catalog" in caplog.text
