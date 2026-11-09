"""Unit tests for :class:`SemanticCacheService`."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.application.cache import SemanticCacheService
from app.domain import (
    CacheFingerprint,
    ChatAnswer,
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
ANSWER = ChatAnswer(respostas=["Marmitaria Central", "Café São João"])


def _match(response: str, distance: float) -> SemanticCacheMatch:
    return SemanticCacheMatch(
        input_text="pergunta", response=response, distance=distance, similarity=1 - distance
    )


def _service(matches: list[SemanticCacheMatch] | None = None) -> tuple[SemanticCacheService, AsyncMock]:
    repository = AsyncMock()
    repository.find_nearest.return_value = matches or []
    return SemanticCacheService(repository), repository


@pytest.mark.asyncio
async def test_should_return_every_match_in_repository_order() -> None:
    # Arrange
    matches = [_match("Melhor", 0.1), _match("Pior", 0.5)]
    service, repository = _service(matches)

    # Act
    result = await service.find_answer(FINGERPRINT, EMBEDDING)

    # Assert
    assert result == matches
    repository.find_nearest.assert_awaited_once_with(EMBEDDING, FINGERPRINT)


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
    assert entry.response == '{"respostas": ["Marmitaria Central", "Café São João"]}'
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
@pytest.mark.parametrize("items", [[], ["", "   "]])
async def test_should_not_store_answer_without_items(items: list[str]) -> None:
    # Arrange
    service, repository = _service()

    # Act
    await service.store(FINGERPRINT, QUESTION, ChatAnswer(respostas=items), EMBEDDING)

    # Assert
    repository.save.assert_not_awaited()
