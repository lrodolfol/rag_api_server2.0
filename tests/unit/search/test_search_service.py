"""Unit tests for :class:`SearchService` with mocked dependencies."""

from unittest.mock import AsyncMock

import pytest

from app.application.cache import build_cache_key, build_fingerprint
from app.application.search import SearchService
from app.application.search import service as search_service
from app.domain import (
    MessageHistoryItem,
    MessageRole,
    OpenIaException,
    SemanticCacheMatch,
)
from app.infrastructure.config import FingerPrintConfig
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.redis import HistoryChannel

Mocks = tuple[SearchService, AsyncMock, AsyncMock, AsyncMock]
CacheMocks = tuple[SearchService, AsyncMock, AsyncMock, AsyncMock, AsyncMock]

FINGER_PRINT = FingerPrintConfig(
    prompt_version="1.0.0", rules_version="1.0.0", model_capability="economic"
)


INTRO = "Encontrei para você:"
NOT_FOUND = "Nada encontrado."


@pytest.fixture(autouse=True)
def _fixed_search_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the random intro and not-found messages with a single fixed one."""
    monkeypatch.setattr(search_service, "_ANSWER_MESSAGES", (INTRO,))
    monkeypatch.setattr(search_service, "_NOT_FOUND_MESSAGES", (NOT_FOUND,))


def _with_intro(answer: str) -> str:
    return f"{INTRO}\n\n{answer}"


def _match(text: str, score: float = 0.95) -> VectorMatch:
    return VectorMatch(id="id", score=score, text=text, user_code="123")


def _semantic_match(response: str, similarity: float) -> SemanticCacheMatch:
    return SemanticCacheMatch(
        input_text="pergunta", response=response, distance=1 - similarity, similarity=similarity
    )


class _Mocks:
    """Service under test plus every mocked collaborator."""

    def __init__(
        self,
        *,
        answer: str,
        matches: list[VectorMatch] | None,
        history: list[MessageHistoryItem] | None,
        cached_answer: str | None,
        semantic_matches: list[SemanticCacheMatch],
    ) -> None:
        self.openai = AsyncMock()
        self.openai.generate_embedding_for_question.return_value = [0.1, 0.2]
        self.openai.generate_chat_answer.return_value = answer
        self.vectors = AsyncMock()
        self.vectors.query.return_value = (
            matches if matches is not None else [_match("Padaria Central")]
        )
        self.history = AsyncMock()
        self.history.get_history.return_value = history if history is not None else []
        self.answer_cache = AsyncMock()
        self.answer_cache.get.return_value = cached_answer
        self.semantic_cache = AsyncMock()
        self.semantic_cache.find_answer.return_value = semantic_matches
        self.service = SearchService(
            openai_service=self.openai,
            vector_repository=self.vectors,
            history_repository=self.history,
            answer_cache=self.answer_cache,
            semantic_cache=self.semantic_cache,
            fingerprint_config=FINGER_PRINT,
        )


def _mocks(
    *,
    answer: str = "Padaria Central",
    matches: list[VectorMatch] | None = None,
    history: list[MessageHistoryItem] | None = None,
    cached_answer: str | None = None,
    semantic_matches: list[SemanticCacheMatch] | None = None,
) -> _Mocks:
    return _Mocks(
        answer=answer,
        matches=matches,
        history=history,
        cached_answer=cached_answer,
        semantic_matches=semantic_matches if semantic_matches is not None else [],
    )


def _service_with_cache(
    *,
    answer: str = "Padaria Central",
    matches: list[VectorMatch] | None = None,
    history: list[MessageHistoryItem] | None = None,
    cached_answer: str | None = None,
) -> CacheMocks:
    mocks = _mocks(
        answer=answer, matches=matches, history=history, cached_answer=cached_answer
    )
    return mocks.service, mocks.openai, mocks.vectors, mocks.history, mocks.answer_cache


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
    assert answer == _with_intro("Padaria Central")
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


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["", "   "])
async def test_should_return_not_found_message_when_answer_is_empty(answer: str) -> None:
    # Arrange
    service, _, _, _ = _service(answer=answer)

    # Act
    result = await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    assert result == NOT_FOUND


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
    assert answer == _with_intro("Resposta em cache")
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
    assert answer == _with_intro("Padaria Central")
    openai.generate_chat_answer.assert_awaited_once()
    answer_cache.set.assert_awaited_once_with(
        _expected_key("onde comer?"), "Padaria Central"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer", ["", "   "]
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
    assert answer == _with_intro("Padaria Central")
    vectors.query.assert_awaited_once()
    openai.generate_chat_answer.assert_awaited_once()


# --- Embedding generated once per request --------------------------------------


@pytest.mark.asyncio
async def test_should_embed_normalized_question_once_on_cache_miss() -> None:
    # Arrange
    service, openai, _, _, _ = _service_with_cache()

    # Act
    await service.search(HistoryChannel.WHATSAPP, "5535999", "  Onde VOCÊ vende   marmitas ")

    # Assert
    openai.generate_embedding_for_question.assert_awaited_once_with(
        "onde voce vende marmitas"
    )


@pytest.mark.asyncio
async def test_should_query_vector_store_with_the_generated_embedding() -> None:
    # Arrange
    service, openai, vectors, _, _ = _service_with_cache()
    openai.generate_embedding_for_question.return_value = [0.3, 0.4, 0.5]

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "Onde comer?")

    # Assert
    vectors.query.assert_awaited_once_with([0.3, 0.4, 0.5])


@pytest.mark.asyncio
async def test_should_not_embed_question_on_cache_hit() -> None:
    # Arrange
    service, openai, _, _, _ = _service_with_cache(cached_answer="Resposta em cache")

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "Onde comer?")

    # Assert
    openai.generate_embedding_for_question.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_propagate_embedding_failure() -> None:
    # Arrange
    service, openai, vectors, _, answer_cache = _service_with_cache()
    openai.generate_embedding_for_question.side_effect = OpenIaException("boom")

    # Act / Assert
    with pytest.raises(OpenIaException):
        await service.search(HistoryChannel.ONLINE, "123", "Onde comer?")
    vectors.query.assert_not_awaited()
    answer_cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_keep_original_question_for_llm_and_history() -> None:
    # Arrange
    service, openai, _, history_repo, _ = _service_with_cache()
    question = "  Onde VOCÊ vende   marmitas "

    # Act
    await service.search(HistoryChannel.ONLINE, "123", question)

    # Assert
    payload, _ = openai.generate_chat_answer.await_args.args
    assert payload.question == question
    assert history_repo.append_message.await_args_list[0].args[2].text == question


# --- Semantic cache -----------------------------------------------------------

QUESTION = "Onde vende marmitas?"
EXPECTED_FINGERPRINT = build_fingerprint(QUESTION, FINGER_PRINT)
SEMANTIC_HIT = [_semantic_match("Marmitaria Central", 0.97)]


@pytest.mark.asyncio
async def test_should_not_consult_semantic_cache_on_exact_hit() -> None:
    # Arrange
    mocks = _mocks(cached_answer="Resposta em cache")

    # Act
    await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    mocks.semantic_cache.find_answer.assert_not_awaited()
    mocks.semantic_cache.store.assert_not_awaited()
    mocks.openai.generate_embedding_for_question.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_return_semantic_answer_without_rag_or_llm() -> None:
    # Arrange
    mocks = _mocks(semantic_matches=SEMANTIC_HIT)

    # Act
    answer = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert answer == _with_intro("Marmitaria Central")
    mocks.semantic_cache.find_answer.assert_awaited_once_with(EXPECTED_FINGERPRINT, [0.1, 0.2])
    mocks.vectors.query.assert_not_awaited()
    mocks.openai.generate_chat_answer.assert_not_awaited()
    mocks.history.get_history.assert_not_awaited()
    mocks.semantic_cache.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_store_semantic_answer_in_exact_cache_and_history() -> None:
    # Arrange
    mocks = _mocks(semantic_matches=SEMANTIC_HIT)

    # Act
    await mocks.service.search(HistoryChannel.WHATSAPP, "5535999", QUESTION)

    # Assert
    mocks.answer_cache.set.assert_awaited_once_with(
        _expected_key(QUESTION), "Marmitaria Central"
    )
    appended = mocks.history.append_message.await_args_list
    assert [call.args[2].role for call in appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert appended[0].args[2].text == QUESTION
    assert appended[1].args[2].text == "Marmitaria Central"


@pytest.mark.asyncio
async def test_should_run_rag_and_store_in_both_caches_on_semantic_miss() -> None:
    # Arrange
    mocks = _mocks(answer="Padaria Central")
    mocks.openai.generate_embedding_for_question.return_value = [0.7, 0.8]

    # Act
    answer = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert answer == _with_intro("Padaria Central")
    mocks.vectors.query.assert_awaited_once_with([0.7, 0.8])
    mocks.openai.generate_chat_answer.assert_awaited_once()
    mocks.answer_cache.set.assert_awaited_once_with(_expected_key(QUESTION), "Padaria Central")
    mocks.semantic_cache.store.assert_awaited_once_with(
        EXPECTED_FINGERPRINT, QUESTION, "Padaria Central", [0.7, 0.8]
    )


@pytest.mark.asyncio
async def test_should_run_rag_when_all_semantic_matches_are_below_threshold() -> None:
    # Arrange
    mocks = _mocks(
        answer="Padaria Central",
        semantic_matches=[_semantic_match("Marmitaria Central", 0.90)],
    )

    # Act
    answer = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert answer == _with_intro("Padaria Central")
    mocks.openai.generate_chat_answer.assert_awaited_once()
    mocks.answer_cache.set.assert_awaited_once_with(_expected_key(QUESTION), "Padaria Central")
    mocks.semantic_cache.store.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_return_joined_answers_of_matches_above_threshold() -> None:
    # Arrange
    mocks = _mocks(
        semantic_matches=[
            _semantic_match("Marmitaria Central", 0.98),
            _semantic_match("Padaria Longe", 0.50),
            _semantic_match("Marmitaria do Bairro", 0.93),
        ]
    )

    # Act
    answer = await mocks.service.search(HistoryChannel.WHATSAPP, "5535999", QUESTION)

    # Assert
    expected = "Marmitaria Central\n\nMarmitaria do Bairro"
    assert answer == _with_intro(expected)
    mocks.openai.generate_chat_answer.assert_not_awaited()
    mocks.answer_cache.set.assert_awaited_once_with(_expected_key(QUESTION), expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["", "   "])
async def test_should_not_store_non_cacheable_answer_in_any_cache(answer: str) -> None:
    # Arrange
    mocks = _mocks(answer=answer)

    # Act
    await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    mocks.answer_cache.set.assert_not_awaited()
    mocks.semantic_cache.store.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("semantic_matches", [[], SEMANTIC_HIT])
async def test_should_embed_question_once_on_exact_miss(
    semantic_matches: list[SemanticCacheMatch],
) -> None:
    # Arrange
    mocks = _mocks(semantic_matches=semantic_matches)

    # Act
    await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    mocks.openai.generate_embedding_for_question.assert_awaited_once_with(
        EXPECTED_FINGERPRINT.normalized_text
    )


# --- Similarity threshold -----------------------------------------------------


def test_should_use_fixed_similarity_threshold() -> None:
    # Assert
    assert SearchService.SIMILARITY_THRESHOLD == 0.91


def test_should_return_none_when_there_are_no_matches() -> None:
    # Act
    answer = SearchService.threshold_evaluate([])

    # Assert
    assert answer is None


def test_should_return_none_when_all_matches_are_below_threshold() -> None:
    # Arrange
    matches = [_semantic_match("Padaria A", 0.90), _semantic_match("Padaria B", 0.5)]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer is None


def test_should_accept_match_exactly_at_threshold() -> None:
    # Arrange
    matches = [_semantic_match("Padaria A", SearchService.SIMILARITY_THRESHOLD)]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == "Padaria A"


def test_should_join_accepted_answers_in_received_order() -> None:
    # Arrange
    matches = [_semantic_match("Padaria A", 0.99), _semantic_match("Padaria B", 0.95)]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == "Padaria A\n\nPadaria B"


def test_should_ignore_matches_below_threshold_among_accepted_ones() -> None:
    # Arrange
    matches = [
        _semantic_match("Padaria A", 0.98),
        _semantic_match("Padaria B", 0.80),
        _semantic_match("Padaria C", 0.92),
    ]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == "Padaria A\n\nPadaria C"


def test_should_not_repeat_duplicated_accepted_answers() -> None:
    # Arrange
    matches = [
        _semantic_match("Padaria A", 0.99),
        _semantic_match("Padaria B", 0.97),
        _semantic_match("Padaria A", 0.95),
    ]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == "Padaria A\n\nPadaria B"
