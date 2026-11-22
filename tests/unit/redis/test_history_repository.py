"""Unit tests for :class:`RedisHistoryRepository` using an in-memory fake Redis."""

import json
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import RedisError

from app.domain import (
    HistoryStoreError,
    MessageContext,
    MessageHistoryItem,
    MessageRole,
)
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
async def test_should_round_trip_message_with_context(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)
    matches = ["Name: sabor_da_roca\nAddress: rua das flores", "Name: padaria_central"]
    message = MessageHistoryItem(
        role=MessageRole.ASSISTANT,
        text="O Sabor da Roca oferece refeicoes caseiras.",
        context=MessageContext(rag_matches=matches),
    )

    # Act
    await repository.append_message(HistoryChannel.ONLINE, "123", message)
    history = await repository.get_history(HistoryChannel.ONLINE, "123")

    # Assert
    assert history == [message]
    assert history[0].context is not None
    assert history[0].context.rag_matches == matches


@pytest.mark.asyncio
async def test_should_omit_context_key_when_message_has_no_context(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)

    # Act
    await repository.append_message(
        HistoryChannel.ONLINE, "123", _message(MessageRole.USER, "ola")
    )

    # Assert
    raw_items = await client.lrange("users_histotic_online:123", 0, -1)
    assert json.loads(raw_items[0]) == {"role": "user", "text": "ola"}


@pytest.mark.asyncio
async def test_should_read_legacy_item_without_context(
    client: FakeAsyncRedis,
) -> None:
    # Arrange
    repository = RedisHistoryRepository(client)
    await client.rpush(
        "users_histotic_online:123",
        json.dumps({"role": "assistant", "text": "Padaria Central"}),
    )

    # Act
    history = await repository.get_history(HistoryChannel.ONLINE, "123")

    # Assert
    assert history == [_message(MessageRole.ASSISTANT, "Padaria Central")]
    assert history[0].context is None
