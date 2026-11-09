"""Integration tests for the Redis history repository with a fake Redis server.

No real Redis is used: ``fakeredis`` provides an in-memory, protocol-accurate
async server so the per-user and per-channel key isolation of the history is
exercised end to end through the repository.
"""

import pytest
from fakeredis import FakeAsyncRedis

from app.domain import MessageHistoryItem, MessageRole
from app.infrastructure.redis import (
    HistoryChannel,
    RedisHistoryRepository,
)


@pytest.fixture
def repository() -> RedisHistoryRepository:
    return RedisHistoryRepository(FakeAsyncRedis(decode_responses=True))


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
