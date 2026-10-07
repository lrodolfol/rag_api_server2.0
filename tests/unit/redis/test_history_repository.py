"""Unit tests for :class:`RedisHistoryRepository` using an in-memory fake Redis."""

from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import RedisError

from app.domain import HistoryStoreError, MessageHistoryItem, MessageRole
from app.infrastructure.redis import (
    HISTORY_TTL_SECONDS,
    HistoryChannel,
    RedisHistoryRepository,
)


@pytest.fixture
def client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


def _message(role: MessageRole, text: str) -> MessageHistoryItem:
    return MessageHistoryItem(role=role, text=text)


@pytest.mark.asyncio
async def test_should_return_empty_history_when_absent(client: FakeAsyncRedis) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)

    # Act
    history = await repository.get_history(HistoryChannel.ONLINE, "123")

    # Assert
    assert history == []


@pytest.mark.asyncio
async def test_should_append_and_return_history_in_order(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)
    first = _message(MessageRole.USER, "onde posso comer?")
    second = _message(MessageRole.ASSISTANT, "Padaria Central")

    # Act
    await repository.append_message(HistoryChannel.ONLINE, "123", first)
    await repository.append_message(HistoryChannel.ONLINE, "123", second)
    history = await repository.get_history(HistoryChannel.ONLINE, "123")

    # Assert
    assert history == [first, second]


@pytest.mark.asyncio
async def test_should_isolate_history_between_channels(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)
    whatsapp_message = _message(MessageRole.USER, "via whatsapp")
    online_message = _message(MessageRole.USER, "via online")

    # Act: same user code, different channels.
    await repository.append_message(HistoryChannel.WHATSAPP, "123", whatsapp_message)
    await repository.append_message(HistoryChannel.ONLINE, "123", online_message)

    # Assert
    assert await repository.get_history(HistoryChannel.WHATSAPP, "123") == [
        whatsapp_message
    ]
    assert await repository.get_history(HistoryChannel.ONLINE, "123") == [
        online_message
    ]


@pytest.mark.asyncio
async def test_should_refresh_thirty_minute_ttl_on_append(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)

    # Act
    await repository.append_message(
        HistoryChannel.ONLINE, "123", _message(MessageRole.USER, "ola")
    )

    # Assert
    ttl = await client.ttl("users_histotic_online:123")
    assert 0 < ttl <= HISTORY_TTL_SECONDS


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_read() -> None:
    # Arrange
    failing_client = AsyncMock()
    failing_client.lrange.side_effect = RedisError("connection refused")
    repository = RedisHistoryRepository(failing_client)

    # Act / Assert
    with pytest.raises(HistoryStoreError):
        await repository.get_history(HistoryChannel.ONLINE, "123")


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_append() -> None:
    # Arrange
    failing_client = AsyncMock()
    failing_client.rpush.side_effect = RedisError("connection refused")
    repository = RedisHistoryRepository(failing_client)

    # Act / Assert
    with pytest.raises(HistoryStoreError):
        await repository.append_message(
            HistoryChannel.ONLINE, "123", _message(MessageRole.USER, "ola")
        )
