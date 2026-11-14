"""Integration tests: ``save`` → ``find_nearest`` / ``delete_by_category`` on a mocked psycopg.

The ``semantic_cache_db`` fixture (``tests/integration/conftest.py``) keeps the
inserted rows in memory and answers the nearest neighbour query by computing the
cosine distance in Python, mimicking pgvector. It also renders the composed SQL
to validate the configured table name.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg
import pytest

from app.domain import CacheFingerprint, ChatAnswer, SemanticCacheEntry
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
    question: str,
    answer: str,
    embedding: list[float],
    prompt_version: str = "1.0.0",
    category: str | None = None,
) -> SemanticCacheEntry:
    return SemanticCacheEntry(
        id=uuid4(),
        fingerprint=_fingerprint(question.lower(), prompt_version),
        input_text=question,
        response=answer,
        embedding=embedding,
        created_at=datetime(2026, 11, 2, 12, 0, 0),
        category=category,
    )


async def _save_one_entry_per_category(repository: PostgresSemanticCacheRepository) -> None:
    await repository.save(
        _entry("Onde vende marmitas?", "Marmitaria", [1.0, 0.0], category="alimentacao")
    )
    await repository.save(_entry("Onde cortar o cabelo?", "Salao", [0.0, 1.0], category="beleza"))
    await repository.save(_entry("O que tem aberto?", "Sem categoria", [0.7, 0.7]))


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
async def test_should_return_category_of_each_match(semantic_cache_db: Any) -> None:
    # Arrange
    repository = _repository()
    await _save_one_entry_per_category(repository)

    # Act
    matches = await repository.find_nearest([1.0, 0.0], _fingerprint("onde vende marmita"))

    # Assert
    categories = {match.response: match.category for match in matches}
    assert categories == {"Marmitaria": "alimentacao", "Salao": "beleza", "Sem categoria": None}


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


@pytest.mark.asyncio
async def test_should_store_and_read_chat_answer_json_response(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    answer = ChatAnswer(respostas=["Marmitaria São João", "Marmitaria Central"])
    await repository.save(_entry("Onde vende marmitas?", answer.to_json(), [1.0, 0.0]))

    # Act
    matches = await repository.find_nearest([1.0, 0.0], _fingerprint("onde vende marmitas?"))

    # Assert
    assert len(matches) == 1
    assert ChatAnswer.from_json(matches[0].response) == answer


# --- delete_by_category ------------------------------------------------------


@pytest.mark.asyncio
async def test_should_delete_category_entries_and_uncategorized_ones(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    await _save_one_entry_per_category(repository)

    # Act
    await repository.delete_by_category("alimentacao")

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza"]
    matches = await repository.find_nearest([1.0, 0.0], _fingerprint("qualquer"))
    assert [match.response for match in matches] == ["Salao"]


@pytest.mark.asyncio
async def test_should_delete_only_uncategorized_entries_when_category_is_none(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    await _save_one_entry_per_category(repository)

    # Act
    await repository.delete_by_category(None)

    # Assert
    assert sorted(row["category"] for row in semantic_cache_db.rows) == ["alimentacao", "beleza"]


@pytest.mark.asyncio
async def test_should_persist_category_column_on_save(semantic_cache_db: Any) -> None:
    # Arrange
    repository = _repository()

    # Act
    await repository.save(_entry("Pergunta", "Resposta", [1.0, 0.0], category="beleza"))
    await repository.save(_entry("Outra", "Resposta", [0.0, 1.0]))

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza", None]
    assert "category" in semantic_cache_db.statements[0]


@pytest.mark.asyncio
async def test_should_not_fail_when_deleting_from_empty_table(semantic_cache_db: Any) -> None:
    # Act
    await _repository().delete_by_category("alimentacao")

    # Assert
    delete_sql = semantic_cache_db.statements[0]
    assert f'DELETE FROM "{TABLE}"' in delete_sql
    assert semantic_cache_db.rows == []


@pytest.mark.asyncio
async def test_should_keep_entries_and_not_raise_when_delete_fails(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    repository = _repository()
    await _save_one_entry_per_category(repository)
    semantic_cache_db.error = psycopg.OperationalError("server closed the connection")

    # Act
    await repository.delete_by_category("alimentacao")

    # Assert
    assert len(semantic_cache_db.rows) == 3
