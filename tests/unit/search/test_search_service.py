"""Unit tests for :class:`SearchService` with mocked dependencies."""

import logging
from unittest.mock import AsyncMock

import pytest

from app.application.cache import build_cache_key, build_fingerprint
from app.application.search import SearchService
from app.application.search import service as search_service
from app.domain import (
    ChatAnswer,
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
BELOW_THRESHOLD = SearchService.SIMILARITY_THRESHOLD - 0.01
DEFAULT_ANSWER = ChatAnswer(respostas=["Padaria Central"])


@pytest.fixture(autouse=True)
def _fixed_search_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the random intro and not-found messages with a single fixed one."""
    monkeypatch.setattr(search_service, "_ANSWER_MESSAGES", (INTRO,))
    monkeypatch.setattr(search_service, "_NOT_FOUND_MESSAGES", (NOT_FOUND,))


def _json(*items: str) -> str:
    return ChatAnswer(respostas=list(items)).to_json()


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
        answer: ChatAnswer,
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
    answer: ChatAnswer = DEFAULT_ANSWER,
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
    answer: ChatAnswer = DEFAULT_ANSWER,
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
    answer: ChatAnswer = DEFAULT_ANSWER,
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
async def test_should_run_pipeline_and_return_intro_followed_by_items() -> None:
    # Arrange
    answer = ChatAnswer(respostas=["Padaria Central", "Café São João"])
    service, openai, vectors, _ = _service(answer=answer)

    # Act
    messages = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert messages == [INTRO, "Padaria Central", "Café São João"]
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
async def test_should_persist_question_and_joined_items_on_given_channel() -> None:
    # Arrange
    answer = ChatAnswer(respostas=["Padaria Central", "Café São João"])
    service, _, _, history_repo = _service(answer=answer)

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
    assert appended[1].args[2].text == "Padaria Central\n\nCafé São João"


@pytest.mark.asyncio
async def test_should_not_persist_assistant_turn_when_answer_is_empty() -> None:
    # Arrange
    service, _, _, history_repo = _service(answer=ChatAnswer())

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
@pytest.mark.parametrize("items", [[], ["", "   "]])
async def test_should_return_single_not_found_message_when_answer_is_empty(
    items: list[str],
) -> None:
    # Arrange
    service, _, _, _ = _service(answer=ChatAnswer(respostas=items))

    # Act
    messages = await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    assert messages == [NOT_FOUND]


# --- Answer cache -------------------------------------------------------------


@pytest.mark.asyncio
async def test_should_return_cached_answer_without_calling_openai_or_pinecone() -> None:
    # Arrange
    service, openai, vectors, history_repo, answer_cache = _service_with_cache(
        cached_answer=_json("Resposta 1", "Resposta 2")
    )

    # Act
    messages = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert messages == [INTRO, "Resposta 1", "Resposta 2"]
    answer_cache.get.assert_awaited_once_with(_expected_key("onde comer?"))
    openai.generate_embedding_for_question.assert_not_awaited()
    openai.generate_chat_answer.assert_not_awaited()
    vectors.query.assert_not_awaited()
    history_repo.get_history.assert_not_awaited()
    answer_cache.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_persist_turn_in_history_on_cache_hit() -> None:
    # Arrange
    service, _, _, history_repo, _ = _service_with_cache(
        cached_answer=_json("Resposta 1", "Resposta 2")
    )

    # Act
    await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    appended = history_repo.append_message.await_args_list
    assert [call.args[2].role for call in appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert appended[1].args[2].text == "Resposta 1\n\nResposta 2"


@pytest.mark.asyncio
async def test_should_treat_corrupted_cached_value_as_miss(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    service, openai, _, _, answer_cache = _service_with_cache(
        cached_answer="texto puro antigo"
    )

    # Act
    with caplog.at_level(logging.WARNING):
        messages = await service.search(HistoryChannel.ONLINE, "123", "onde comer?")

    # Assert
    assert messages == [INTRO, "Padaria Central"]
    openai.generate_chat_answer.assert_awaited_once()
    answer_cache.set.assert_awaited_once_with(
        _expected_key("onde comer?"), _json("Padaria Central")
    )
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert "texto puro antigo" not in caplog.text


@pytest.mark.asyncio
async def test_should_run_pipeline_and_cache_answer_json_on_miss() -> None:
    # Arrange
    service, openai, _, _, answer_cache = _service_with_cache()

    # Act
    messages = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert messages == [INTRO, "Padaria Central"]
    openai.generate_chat_answer.assert_awaited_once()
    answer_cache.set.assert_awaited_once_with(
        _expected_key("onde comer?"), _json("Padaria Central")
    )


@pytest.mark.asyncio
async def test_should_not_cache_empty_answer() -> None:
    # Arrange
    service, _, _, _, answer_cache = _service_with_cache(answer=ChatAnswer())

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
    messages = await service.search(HistoryChannel.WHATSAPP, "5535999", "onde comer?")

    # Assert
    assert messages == [INTRO, "Padaria Central"]
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
    service, openai, _, _, _ = _service_with_cache(cached_answer=_json("Resposta em cache"))

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
SEMANTIC_HIT = [_semantic_match(_json("Marmitaria Central"), 0.97)]


@pytest.mark.asyncio
async def test_should_not_consult_semantic_cache_on_exact_hit() -> None:
    # Arrange
    mocks = _mocks(cached_answer=_json("Resposta em cache"))

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
    messages = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert messages == [INTRO, "Marmitaria Central"]
    mocks.semantic_cache.find_answer.assert_awaited_once_with(EXPECTED_FINGERPRINT, [0.1, 0.2])
    mocks.vectors.query.assert_not_awaited()
    mocks.openai.generate_chat_answer.assert_not_awaited()
    mocks.history.get_history.assert_not_awaited()
    mocks.semantic_cache.store.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_store_semantic_answer_json_in_exact_cache_and_text_in_history() -> None:
    # Arrange
    mocks = _mocks(semantic_matches=SEMANTIC_HIT)

    # Act
    await mocks.service.search(HistoryChannel.WHATSAPP, "5535999", QUESTION)

    # Assert
    mocks.answer_cache.set.assert_awaited_once_with(
        _expected_key(QUESTION), _json("Marmitaria Central")
    )
    appended = mocks.history.append_message.await_args_list
    assert [call.args[2].role for call in appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert appended[0].args[2].text == QUESTION
    assert appended[1].args[2].text == "Marmitaria Central"


@pytest.mark.asyncio
async def test_should_merge_accepted_semantic_matches_without_duplicates() -> None:
    # Arrange
    mocks = _mocks(
        semantic_matches=[
            _semantic_match(_json("Marmitaria Central", "Padaria A"), 0.98),
            _semantic_match(_json("Padaria Longe"), 0.50),
            _semantic_match(_json("Padaria A", "Marmitaria do Bairro"), 0.93),
        ]
    )

    # Act
    messages = await mocks.service.search(HistoryChannel.WHATSAPP, "5535999", QUESTION)

    # Assert
    expected_items = ["Marmitaria Central", "Padaria A", "Marmitaria do Bairro"]
    assert messages == [INTRO, *expected_items]
    mocks.openai.generate_chat_answer.assert_not_awaited()
    mocks.answer_cache.set.assert_awaited_once_with(
        _expected_key(QUESTION), _json(*expected_items)
    )


@pytest.mark.asyncio
async def test_should_run_rag_and_store_json_in_both_caches_on_semantic_miss() -> None:
    # Arrange
    mocks = _mocks()
    mocks.openai.generate_embedding_for_question.return_value = [0.7, 0.8]

    # Act
    messages = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert messages == [INTRO, "Padaria Central"]
    mocks.vectors.query.assert_awaited_once_with([0.7, 0.8])
    mocks.openai.generate_chat_answer.assert_awaited_once()
    mocks.answer_cache.set.assert_awaited_once_with(
        _expected_key(QUESTION), _json("Padaria Central")
    )
    mocks.semantic_cache.store.assert_awaited_once_with(
        EXPECTED_FINGERPRINT, QUESTION, DEFAULT_ANSWER, [0.7, 0.8]
    )


@pytest.mark.asyncio
async def test_should_run_rag_when_all_semantic_matches_are_below_threshold() -> None:
    # Arrange
    mocks = _mocks(semantic_matches=[_semantic_match(_json("Marmitaria Central"), BELOW_THRESHOLD)])

    # Act
    messages = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert messages == [INTRO, "Padaria Central"]
    mocks.openai.generate_chat_answer.assert_awaited_once()
    mocks.answer_cache.set.assert_awaited_once_with(
        _expected_key(QUESTION), _json("Padaria Central")
    )
    mocks.semantic_cache.store.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_run_rag_when_semantic_match_is_corrupted() -> None:
    # Arrange
    mocks = _mocks(semantic_matches=[_semantic_match("texto puro antigo", 0.99)])

    # Act
    messages = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert messages == [INTRO, "Padaria Central"]
    mocks.openai.generate_chat_answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_not_store_empty_answer_in_any_cache() -> None:
    # Arrange
    mocks = _mocks(answer=ChatAnswer())

    # Act
    messages = await mocks.service.search(HistoryChannel.ONLINE, "123", QUESTION)

    # Assert
    assert messages == [NOT_FOUND]
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
    # Act / Assert
    assert SearchService.threshold_evaluate([]) is None


def test_should_return_none_when_all_matches_are_below_threshold() -> None:
    # Arrange
    matches = [
        _semantic_match(_json("Padaria A"), BELOW_THRESHOLD),
        _semantic_match(_json("Padaria B"), 0.5),
    ]

    # Act / Assert
    assert SearchService.threshold_evaluate(matches) is None


def test_should_accept_match_exactly_at_threshold() -> None:
    # Arrange
    matches = [_semantic_match(_json("Padaria A"), SearchService.SIMILARITY_THRESHOLD)]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == ChatAnswer(respostas=["Padaria A"])


def test_should_merge_accepted_answers_in_received_order() -> None:
    # Arrange
    matches = [
        _semantic_match(_json("Padaria A", "Padaria B"), 0.99),
        _semantic_match(_json("Padaria C"), 0.95),
    ]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == ChatAnswer(respostas=["Padaria A", "Padaria B", "Padaria C"])


def test_should_ignore_matches_below_threshold_among_accepted_ones() -> None:
    # Arrange
    matches = [
        _semantic_match(_json("Padaria A"), 0.98),
        _semantic_match(_json("Padaria B"), BELOW_THRESHOLD),
        _semantic_match(_json("Padaria C"), 0.92),
    ]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == ChatAnswer(respostas=["Padaria A", "Padaria C"])


def test_should_not_repeat_duplicated_items_across_accepted_answers() -> None:
    # Arrange
    matches = [
        _semantic_match(_json("Padaria A", "Padaria B"), 0.99),
        _semantic_match(_json("Padaria B"), 0.97),
        _semantic_match(_json("Padaria A", "Padaria C"), 0.95),
    ]

    # Act
    answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == ChatAnswer(respostas=["Padaria A", "Padaria B", "Padaria C"])


def test_should_ignore_corrupted_match_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    matches = [
        _semantic_match("texto puro antigo", 0.99),
        _semantic_match(_json("Padaria A"), 0.95),
    ]

    # Act
    with caplog.at_level(logging.WARNING):
        answer = SearchService.threshold_evaluate(matches)

    # Assert
    assert answer == ChatAnswer(respostas=["Padaria A"])
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    assert "texto puro antigo" not in caplog.text


def test_should_return_none_when_accepted_answers_have_no_items() -> None:
    # Arrange
    matches = [_semantic_match(_json(), 0.99)]

    # Act / Assert
    assert SearchService.threshold_evaluate(matches) is None
