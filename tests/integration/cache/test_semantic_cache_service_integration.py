"""Integration tests: ``SemanticCacheService`` on the real repository over a mocked psycopg.

The ``semantic_cache_db`` fixture (``tests/integration/conftest.py``) keeps the
stored rows in memory, answers the nearest-neighbour query and applies the
delete-by-category statement.
"""

from typing import Any

import pytest

from app.application.cache import SemanticCacheService
from app.domain import CacheFingerprint, ChatAnswer
from app.infrastructure.config import PostgresConfig, SemanticCacheConfig
from app.infrastructure.postgres import PostgresSemanticCacheRepository

POSTGRES_CONFIG = PostgresConfig(
    host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
)
SEMANTIC_CACHE_CONFIG = SemanticCacheConfig(table="rag_response_cache", top_k=3)
FOOD_EMBEDDING = [1.0, 0.0]
BEAUTY_EMBEDDING = [0.0, 1.0]
ANY_EMBEDDING = [0.7, 0.7]


def _service() -> SemanticCacheService:
    return SemanticCacheService(
        PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)
    )


def _fingerprint(normalized_text: str) -> CacheFingerprint:
    return CacheFingerprint(
        prompt_version="1.0.0",
        rules_version="1.0.0",
        model_capability="economic",
        normalized_text=normalized_text,
    )


async def _store_one_answer_per_category(service: SemanticCacheService) -> None:
    await service.store(
        _fingerprint("onde vende marmitas?"),
        "Onde vende marmitas?",
        ChatAnswer(respostas=["Marmitaria Central"]),
        FOOD_EMBEDDING,
        category_slug="alimentacao",
    )
    await service.store(
        _fingerprint("onde cortar o cabelo?"),
        "Onde cortar o cabelo?",
        ChatAnswer(respostas=["Salao Bella"]),
        BEAUTY_EMBEDDING,
        category_slug="beleza",
    )
    await service.store(
        _fingerprint("o que tem aberto?"),
        "O que tem aberto?",
        ChatAnswer(respostas=["Padaria Central"]),
        ANY_EMBEDDING,
        category_slug=None,
    )


@pytest.mark.asyncio
async def test_should_store_answers_tagged_with_their_category(semantic_cache_db: Any) -> None:
    # Arrange
    service = _service()

    # Act
    await _store_one_answer_per_category(service)

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == ["alimentacao", "beleza", None]


@pytest.mark.asyncio
async def test_should_keep_only_other_categories_after_invalidation(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    service = _service()
    await _store_one_answer_per_category(service)

    # Act
    await service.invalidate_category("alimentacao")

    # Assert
    matches = await service.find_answer(_fingerprint("qualquer"), FOOD_EMBEDDING)
    assert [ChatAnswer.from_json(match.response).respostas for match in matches] == [
        ["Salao Bella"]
    ]


@pytest.mark.asyncio
async def test_should_drop_only_uncategorized_answers_when_invalidating_none(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    service = _service()
    await _store_one_answer_per_category(service)

    # Act
    await service.invalidate_category(None)

    # Assert
    assert sorted(row["category"] for row in semantic_cache_db.rows) == ["alimentacao", "beleza"]
