"""Unit tests for :class:`SearchService` with mocked dependencies."""

from unittest.mock import AsyncMock

import pytest

from app.application.cache import build_cache_key, build_fingerprint
from app.application.search import SearchService
from app.domain import PATTERN_RESPONSE, MessageHistoryItem, MessageRole
from app.infrastructure.config import FingerPrintConfig
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.redis import HistoryChannel

Mocks = tuple[SearchService, AsyncMock, AsyncMock, AsyncMock]
CacheMocks = tuple[SearchService, AsyncMock, AsyncMock, AsyncMock, AsyncMock]

FINGER_PRINT = FingerPrintConfig(
    prompt_version="1.0.0", rules_version="1.0.0", model_capability="economic"
)


def _match(text: str, score: float = 0.95) -> VectorMatch:
    return VectorMatch(id="id", score=score, text=text, user_code="123")


def _service_with_cache(
    *,
    answer: str = "Padaria Central",
    matches: list[VectorMatch] | None = None,
    history: list[MessageHistoryItem] | None = None,
    cached_answer: str | None = None,
) -> CacheMocks:
    openai = AsyncMock()
    openai.generate_embedding_for_question.return_value = [0.1, 0.2]
    openai.generate_chat_answer.return_value = answer
    vectors = AsyncMock()
    vectors.query.return_value = (
        matches if matches is not None else [_match("Padaria Central")]
    )
    history_repo = AsyncMock()
    history_repo.get_history.return_value = history if history is not None else []
    answer_cache = AsyncMock()
    answer_cache.get.return_value = cached_answer
    service = SearchService(
        openai_service=openai,
        vector_repository=vectors,
        history_repository=history_repo,
        answer_cache=answer_cache,
        fingerprint_config=FINGER_PRINT,
    )
    return service, openai, vectors, history_repo, answer_cache


def _service(
    *,
    answer: str = "Padaria Central",
    matches: list[VectorMatch] | None = None,
    history: list[MessageHistoryItem] | None = None,
) -> Mocks:
    service, openai, vectors, history_repo, _ = _service_with_cache(
        answer=answer, matches=matches, history=history
    )
    return service, openai, vectors, history_repo


def _expected_key(question: str) -> str:
    return build_cache_key(build_fingerprint(question, FINGER_PRINT))


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


# --- Answer cache -------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_return_cached_answer_without_calling_openai_or_pinecone() -> None:
    # Arrange
    service, openai, vectors, history_repo, answer_cache = _service_with_cache(
        cached_answer="Resposta em cache"
    )

    # Act
    answer = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert answer == "Resposta em cache"
    answer_cache.get.assert_awaited_once_with(_expected_key("onde comer?"))
    openai.generate_embedding_for_question.assert_not_awaited()
    openai.generate_chat_answer.assert_not_awaited()
    vectors.query.assert_not_awaited()
    history_repo.get_history.assert_not_awaited()
    answer_cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_persist_turn_in_history_on_cache_hit() -> None:
    # Arrange
    service, _, _, history_repo, _ = _service_with_cache(cached_answer="Resposta em cache")

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    appended = history_repo.append_message.await_args_list
    assert [call.args[2].role for call in appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert appended[1].args[2].text == "Resposta em cache"


@pytest.mark.asyncio
async def test_should_run_pipeline_and_cache_answer_on_miss() -> None:
    # Arrange
    service, openai, _, _, answer_cache = _service_with_cache(answer="Padaria Central")

    # Act
    answer = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert answer == "Padaria Central"
    openai.generate_chat_answer.assert_awaited_once()
    answer_cache.set.assert_awaited_once_with(
        _expected_key("onde comer?"), "Padaria Central"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer", ["", "   ", PATTERN_RESPONSE, f"  {PATTERN_RESPONSE}\n"]
)
async def test_should_not_cache_empty_or_fallback_answer(answer: str) -> None:
    # Arrange
    service, _, _, _, answer_cache = _service_with_cache(answer=answer)

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    answer_cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_use_same_key_for_equivalent_questions() -> None:
    # Arrange
    service, _, _, _, answer_cache = _service_with_cache()

    # Act
    await service.search(HistoryChannel.WHATSAPP, "1", "  Onde COMER?\n")
    await service.search(HistoryChannel.ONLINE, "2", "onde comer?")

    # Assert
    keys = [call.args[0] for call in answer_cache.get.await_args_list]
    assert keys[0] == keys[1] == _expected_key("onde comer?")


@pytest.mark.asyncio
async def test_should_run_pipeline_when_cache_read_fails() -> None:
    # Arrange: the repository already converts Redis failures into a miss (None).
    service, openai, vectors, _, _ = _service_with_cache(cached_answer=None)

    # Act
    answer = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert answer == "Padaria Central"
    vectors.query.assert_awaited_once()
    openai.generate_chat_answer.assert_awaited_once()
