"""Integration tests for the Redis history repository with a fake Redis server.

No real Redis is used: ``fakeredis`` provides an in-memory, protocol-accurate
async server so the per-user and per-channel key isolation of the history is
exercised end to end through the repository.
"""

import pytest
from fakeredis import FakeAsyncRedis

from app.domain import MessageContext, MessageHistoryItem, MessageRole
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


@pytest.mark.asyncio
async def test_should_round_trip_assistant_message_with_context(
    repository: RedisHistoryRepository,
) -> None:
    # Arrange
    question = MessageHistoryItem(role=MessageRole.USER, text="estou com fome")
    answer = MessageHistoryItem(
        role=MessageRole.ASSISTANT,
        text="O Sabor da Roca oferece refeicoes caseiras.",
        context=MessageContext(
            rag_matches=["Name: sabor_da_roca", "Name: padaria_central"]
        ),
    )

    # Act
    await repository.append_message(HistoryChannel.WHATSAPP, "ccc", question)
    await repository.append_message(HistoryChannel.WHATSAPP, "ccc", answer)
    history = await repository.get_history(HistoryChannel.WHATSAPP, "ccc")

    # Assert
    assert history == [question, answer]
    assert history[0].context is None
    assert history[1].context == answer.context
