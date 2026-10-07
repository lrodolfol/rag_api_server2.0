"""Unit tests for :class:`SearchService` with mocked dependencies."""

from unittest.mock import AsyncMock

import pytest

from app.application.search import SearchService
from app.domain import MessageHistoryItem, MessageRole
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.redis import HistoryChannel

Mocks = tuple[SearchService, AsyncMock, AsyncMock, AsyncMock]


def _match(text: str, score: float = 0.95) -> VectorMatch:
    return VectorMatch(id="id", score=score, text=text, user_code="123")


def _service(
    *,
    answer: str = "Padaria Central",
    matches: list[VectorMatch] | None = None,
    history: list[MessageHistoryItem] | None = None,
) -> Mocks:
    openai = AsyncMock()
    openai.generate_embedding_for_question.return_value = [0.1, 0.2]
    openai.generate_chat_answer.return_value = answer
    vectors = AsyncMock()
    vectors.query.return_value = (
        matches if matches is not None else [_match("Padaria Central")]
    )
    history_repo = AsyncMock()
    history_repo.get_history.return_value = history if history is not None else []
    service = SearchService(
        openai_service=openai,
        vector_repository=vectors,
        history_repository=history_repo,
    )
    return service, openai, vectors, history_repo


@pytest.mark.asyncio
async def test_should_run_pipeline_and_return_generated_answer() -> None:
    # Arrange
    service, openai, vectors, _ = _service(answer="Padaria Central")

    # Act
    answer = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert answer == "Padaria Central"
    openai.generate_embedding_for_question.assert_awaited_once_with("onde comer?")
    vectors.query.assert_awaited_once_with([0.1, 0.2])
    openai.generate_chat_answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_pass_matched_texts_as_phrases_and_prior_history() -> None:
    # Arrange
    history = [MessageHistoryItem(role=MessageRole.USER, text="ola")]
    service, openai, _, _ = _service(
        matches=[_match("Padaria A"), _match("Restaurante B")],
        history=history,
    )

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    payload, phrases = openai.generate_chat_answer.await_args.args
    assert phrases == ["Padaria A", "Restaurante B"]
    assert payload.question == "onde comer?"
    assert payload.chat_historic == history


@pytest.mark.asyncio
async def test_should_persist_question_and_answer_turn_on_given_channel() -> None:
    # Arrange
    service, _, _, history_repo = _service(answer="Padaria Central")

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    appended = history_repo.append_message.await_args_list
    assert len(appended) == 2
    assert all(call.args[0] is HistoryChannel.ONLINE for call in appended)
    assert all(call.args[1] == "123" for call in appended)
    assert appended[0].args[2].role is MessageRole.USER
    assert appended[0].args[2].text == "onde comer?"
    assert appended[1].args[2].role is MessageRole.ASSISTANT
    assert appended[1].args[2].text == "Padaria Central"


@pytest.mark.asyncio
async def test_should_not_persist_assistant_turn_when_answer_is_empty() -> None:
    # Arrange
    service, _, _, history_repo = _service(answer="")

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    appended = history_repo.append_message.await_args_list
    assert len(appended) == 1
    assert appended[0].args[2].role is MessageRole.USER


@pytest.mark.asyncio
async def test_should_read_history_before_answering() -> None:
    # Arrange
    service, _, _, history_repo = _service()

    # Act
    await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    history_repo.get_history.assert_awaited_once_with(
        HistoryChannel.WHATSAPP, "5535999"
    )
