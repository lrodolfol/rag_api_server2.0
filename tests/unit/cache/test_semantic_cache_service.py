"""Unit tests for :class:`SemanticCacheService` and the shared caching policy."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.application.cache import SemanticCacheService, is_cacheable_answer
from app.domain import (
    PATTERN_RESPONSE,
    CacheFingerprint,
    SemanticCacheEntry,
    SemanticCacheMatch,
)

FINGERPRINT = CacheFingerprint(
    prompt_version="1.0.0",
    rules_version="1.0.0",
    model_capability="economic",
    normalized_text="onde vende marmitas?",
)
EMBEDDING = [0.1, 0.2, 0.3]
QUESTION = "Onde vende marmitas?"
ANSWER = "Marmitaria Central"


def _match(response: str, distance: float) -> SemanticCacheMatch:
    return SemanticCacheMatch(
        input_text="pergunta", response=response, distance=distance, similarity=1 - distance
    )


def _service(matches: list[SemanticCacheMatch] | None = None) -> tuple[SemanticCacheService, AsyncMock]:
    repository = AsyncMock()
    repository.find_nearest.return_value = matches or []
    return SemanticCacheService(repository), repository


@pytest.mark.asyncio
async def test_should_return_answer_of_best_match() -> None:
    # Arrange
    service, repository = _service([_match("Melhor", 0.1), _match("Pior", 0.5)])

    # Act
    answer = await service.find_answer(FINGERPRINT, EMBEDDING)

    # Assert
    assert answer == "Melhor"
    repository.find_nearest.assert_awaited_once_with(EMBEDDING, FINGERPRINT)


@pytest.mark.asyncio
async def test_should_return_none_when_no_match() -> None:
    # Arrange
    service, _ = _service([])

    # Act
    answer = await service.find_answer(FINGERPRINT, EMBEDDING)

    # Assert
    assert answer is None


@pytest.mark.asyncio
async def test_should_return_best_match_regardless_of_similarity() -> None:
    # Arrange: no minimum similarity threshold in this version.
    service, _ = _service([_match("Distante", 0.95)])

    # Act
    answer = await service.find_answer(FINGERPRINT, EMBEDDING)

    # Assert
    assert answer == "Distante"


@pytest.mark.asyncio
async def test_should_store_entry_with_generated_id_and_creation_time() -> None:
    # Arrange
    service, repository = _service()
    before = datetime.now(UTC).replace(tzinfo=None)

    # Act
    await service.store(FINGERPRINT, QUESTION, ANSWER, EMBEDDING)

    # Assert
    entry: SemanticCacheEntry = repository.save.await_args.args[0]
    assert isinstance(entry.id, UUID)
    assert entry.id.version == 4
    assert entry.fingerprint == FINGERPRINT
    assert entry.input_text == QUESTION
    assert entry.response == ANSWER
    assert entry.embedding == EMBEDDING
    assert before <= entry.created_at <= before + timedelta(seconds=5)


@pytest.mark.asyncio
async def test_should_generate_a_new_id_for_each_entry() -> None:
    # Arrange
    service, repository = _service()

    # Act
    await service.store(FINGERPRINT, QUESTION, ANSWER, EMBEDDING)
    await service.store(FINGERPRINT, QUESTION, ANSWER, EMBEDDING)

    # Assert
    first, second = (call.args[0] for call in repository.save.await_args_list)
    assert first.id != second.id


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["", "   ", PATTERN_RESPONSE, f"  {PATTERN_RESPONSE}\n"])
async def test_should_not_store_empty_or_fallback_answer(answer: str) -> None:
    # Arrange
    service, repository = _service()

    # Act
    await service.store(FINGERPRINT, QUESTION, answer, EMBEDDING)

    # Assert
    repository.save.assert_not_awaited()


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("Padaria Central", True), ("", False), ("  \n", False), (PATTERN_RESPONSE, False)],
)
def test_should_classify_cacheable_answers(answer: str, expected: bool) -> None:
    # Act / Assert
    assert is_cacheable_answer(answer) is expected
