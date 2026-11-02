"""Integration tests: ``save`` → ``find_nearest`` round trip on a mocked psycopg.

The ``semantic_cache_db`` fixture (``tests/integration/conftest.py``) keeps the
inserted rows in memory and answers the nearest neighbour query by computing the
cosine distance in Python, mimicking pgvector. It also renders the composed SQL
to validate the configured table name.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from app.domain import CacheFingerprint, SemanticCacheEntry
from app.infrastructure.config import PostgresConfig, SemanticCacheConfig
from app.infrastructure.postgres import PostgresSemanticCacheRepository

TABLE = "custom_semantic_cache"
POSTGRES_CONFIG = PostgresConfig(
    host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
)


def _repository(top_k: int = 3) -> PostgresSemanticCacheRepository:
    return PostgresSemanticCacheRepository(
        POSTGRES_CONFIG, SemanticCacheConfig(table=TABLE, top_k=top_k)
    )


def _fingerprint(normalized_text: str, prompt_version: str = "1.0.0") -> CacheFingerprint:
    return CacheFingerprint(
        prompt_version=prompt_version,
        rules_version="1.0.0",
        model_capability="economic",
        normalized_text=normalized_text,
    )


def _entry(
    question: str, answer: str, embedding: list[float], prompt_version: str = "1.0.0"
) -> SemanticCacheEntry:
    return SemanticCacheEntry(
        id=uuid4(),
        fingerprint=_fingerprint(question.lower(), prompt_version),
        input_text=question,
        response=answer,
        embedding=embedding,
        created_at=datetime(2026, 11, 2, 12, 0, 0),
    )


@pytest.mark.asyncio
async def test_should_find_saved_answers_ordered_by_similarity(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    await repository.save(_entry("Onde vende marmitas?", "Marmitaria Central", [1.0, 0.0]))
    await repository.save(_entry("Onde tem pizza?", "Pizzaria Bella", [0.0, 1.0]))

    # Act
    matches = await repository.find_nearest([0.9, 0.1], _fingerprint("onde vende marmita"))

    # Assert
    assert [match.response for match in matches] == ["Marmitaria Central", "Pizzaria Bella"]
    assert matches[0].input_text == "Onde vende marmitas?"
    assert matches[0].distance < matches[1].distance
    assert matches[0].similarity == pytest.approx(1 - matches[0].distance)


@pytest.mark.asyncio
async def test_should_ignore_entries_from_other_fingerprint_versions(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    await repository.save(_entry("Onde vende marmitas?", "Antiga", [1.0, 0.0], "0.9.0"))

    # Act
    matches = await repository.find_nearest([1.0, 0.0], _fingerprint("onde vende marmitas?"))

    # Assert
    assert matches == []


@pytest.mark.asyncio
async def test_should_limit_results_to_configured_top_k(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository(top_k=1)
    await repository.save(_entry("Pergunta A", "Resposta A", [1.0, 0.0]))
    await repository.save(_entry("Pergunta B", "Resposta B", [0.0, 1.0]))

    # Act
    matches = await repository.find_nearest([1.0, 0.0], _fingerprint("pergunta"))

    # Assert
    assert [match.response for match in matches] == ["Resposta A"]


@pytest.mark.asyncio
async def test_should_compose_sql_with_configured_table_name(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()

    # Act
    await repository.save(_entry("Pergunta", "Resposta", [1.0, 0.0]))
    await repository.find_nearest([1.0, 0.0], _fingerprint("pergunta"))

    # Assert
    insert_sql, select_sql = semantic_cache_db.statements
    assert f'INSERT INTO "{TABLE}"' in insert_sql
    assert "%(embedding)s::vector" in insert_sql
    assert "%(response_json)s::jsonb" in insert_sql
    assert f'FROM "{TABLE}" c' in select_sql
    assert "ORDER BY c.embedding <=> q.value" in select_sql
    assert "LIMIT %(limit)s" in select_sql
