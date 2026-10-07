"""Integration tests for the Redis history repository with a fake Redis server.

No real Redis is used: ``fakeredis`` provides an in-memory, protocol-accurate
async server so the full history flow (append, per-channel and per-user key
isolation, ordered retrieval and TTL application) is exercised end to end
through the repository.
"""

import pytest
from fakeredis import FakeAsyncRedis

from app.domain import MessageHistoryItem, MessageRole
from app.infrastructure.redis import (
    HISTORY_TTL_SECONDS,
    HistoryChannel,
    RedisHistoryRepository,
)


@pytest.fixture
def repository() -> RedisHistoryRepository:
    return RedisHistoryRepository(FakeAsyncRedis(decode_responses=True))


@pytest.mark.asyncio
async def test_should_persist_full_conversation_flow(
    repository: RedisHistoryRepository,
) -> None:
    # Arrange
    conversation = [
        MessageHistoryItem(role=MessageRole.USER, text="onde posso comer?"),
        MessageHistoryItem(role=MessageRole.ASSISTANT, text="Padaria Central"),
        MessageHistoryItem(role=MessageRole.USER, text="tem delivery?"),
    ]

    # Act
    for message in conversation:
        await repository.append_message(HistoryChannel.WHATSAPP, "5535999999999", message)
    history = await repository.get_history(HistoryChannel.WHATSAPP, "5535999999999")

    # Assert
    assert history == conversation


@pytest.mark.asyncio
async def test_should_keep_users_and_channels_isolated(
    repository: RedisHistoryRepository,
) -> None:
    # Arrange
    message_a = MessageHistoryItem(role=MessageRole.USER, text="usuario A online")
    message_b = MessageHistoryItem(role=MessageRole.USER, text="usuario B whatsapp")

    # Act
    await repository.append_message(HistoryChannel.ONLINE, "aaa", message_a)
    await repository.append_message(HistoryChannel.WHATSAPP, "bbb", message_b)

    # Assert
    assert await repository.get_history(HistoryChannel.ONLINE, "aaa") == [message_a]
    assert await repository.get_history(HistoryChannel.WHATSAPP, "bbb") == [message_b]
    assert await repository.get_history(HistoryChannel.ONLINE, "bbb") == []


@pytest.mark.asyncio
async def test_should_apply_history_ttl_on_each_channel_key() -> None:
    # Arrange
    client = FakeAsyncRedis(decode_responses=True)
    repository = RedisHistoryRepository(client)
    message = MessageHistoryItem(role=MessageRole.USER, text="ola")

    # Act
    await repository.append_message(HistoryChannel.ONLINE, "123", message)

    # Assert
    ttl = await client.ttl("users_histotic_online:123")
    assert 0 < ttl <= HISTORY_TTL_SECONDS
