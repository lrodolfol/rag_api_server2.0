"""Unit tests for :class:`PostgresSemanticCacheRepository` with a fake connection."""

import json
import logging
from datetime import datetime
from typing import Any, Self
from uuid import UUID

import psycopg
import pytest

from app.domain import CacheFingerprint, SemanticCacheEntry, SemanticCacheMatch
from app.infrastructure.config import PostgresConfig, SemanticCacheConfig
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.postgres import semantic_cache_repository as module
from app.infrastructure.postgres.semantic_cache_repository import to_vector_literal

QUESTION = "Onde posso comprar marmitas?"
ANSWER = "Encontrei a Marmitaria Central"
EMBEDDING = [0.1, 0.2, -0.3]
ENTRY_ID = UUID("12345678-1234-5678-1234-567812345678")
CREATED_AT = datetime(2026, 11, 2, 12, 0, 0)
FINGERPRINT = CacheFingerprint(
    prompt_version="1.0.0",
    rules_version="2.0.0",
    model_capability="economic",
    normalized_text="onde posso comprar marmitas?",
)
POSTGRES_CONFIG = PostgresConfig(
    host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
)
SEMANTIC_CACHE_CONFIG = SemanticCacheConfig(table="rag_response_cache", top_k=3)


class FakeCursor:
    """Async cursor double recording the executed query and its parameters."""

    def __init__(self, connection: "FakeConnection") -> None:
        self._connection = connection

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, query: Any, params: dict[str, Any]) -> None:
        await self._connection.execute(query, params)

    async def fetchall(self) -> list[dict[str, Any]]:
        return self._connection.rows


class FakeConnection:
    """Async connection double; ``error`` is raised on execute when set."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []
        self.error: psycopg.Error | None = None
        self.executed: list[tuple[Any, dict[str, Any]]] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def cursor(self, row_factory: Any = None) -> FakeCursor:
        return FakeCursor(self)

    async def execute(self, query: Any, params: dict[str, Any]) -> None:
        if self.error is not None:
            raise self.error
        self.executed.append((query, params))


def _patch_connection(
    monkeypatch: pytest.MonkeyPatch, connection: FakeConnection
) -> None:
    async def _open(_: PostgresConfig) -> FakeConnection:
        return connection

    monkeypatch.setattr(module, "open_postgres_connection", _open)


def _repository() -> PostgresSemanticCacheRepository:
    return PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)


def _entry() -> SemanticCacheEntry:
    return SemanticCacheEntry(
        id=ENTRY_ID,
        fingerprint=FINGERPRINT,
        input_text=QUESTION,
        response=ANSWER,
        embedding=EMBEDDING,
        created_at=CREATED_AT,
    )


def _row(input_text: str, response: str, distance: float) -> dict[str, Any]:
    return {
        "input_text": input_text,
        "response_json": response,
        "distance": distance,
        "similarity": 1 - distance,
    }


def test_should_serialize_vector_in_pgvector_text_format() -> None:
    # Act
    literal = to_vector_literal([0.1, 0.2, -0.3, 1])

    # Assert
    assert literal == "[0.1,0.2,-0.3,1.0]"


@pytest.mark.asyncio
async def test_should_send_fingerprint_limit_and_vector_as_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)

    # Act
    await _repository().find_nearest(EMBEDDING, FINGERPRINT)

    # Assert
    _, params = connection.executed[0]
    assert params == {
        "embedding": "[0.1,0.2,-0.3]",
        "prompt_version": "1.0.0",
        "rules_version": "2.0.0",
        "model_capability": "economic",
        "limit": 3,
    }


@pytest.mark.asyncio
async def test_should_map_rows_to_matches_in_received_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    rows = [_row("pergunta a", "resposta a", 0.1), _row("pergunta b", "resposta b", 0.4)]
    _patch_connection(monkeypatch, FakeConnection(rows))

    # Act
    matches = await _repository().find_nearest(EMBEDDING, FINGERPRINT)

    # Assert
    assert matches == [
        SemanticCacheMatch(
            input_text="pergunta a", response="resposta a", distance=0.1, similarity=0.9
        ),
        SemanticCacheMatch(
            input_text="pergunta b", response="resposta b", distance=0.4, similarity=0.6
        ),
    ]


@pytest.mark.asyncio
async def test_should_return_empty_list_and_log_when_connection_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    async def _failing_open(_: PostgresConfig) -> FakeConnection:
        raise psycopg.OperationalError("connection refused")

    monkeypatch.setattr(module, "open_postgres_connection", _failing_open)

    # Act
    with caplog.at_level(logging.ERROR):
        matches = await _repository().find_nearest(EMBEDDING, FINGERPRINT)

    # Assert
    assert matches == []
    assert "Failed to read semantic cache" in caplog.text


@pytest.mark.asyncio
async def test_should_return_empty_list_and_log_when_query_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    connection = FakeConnection()
    connection.error = psycopg.errors.DataException("different vector dimensions")
    _patch_connection(monkeypatch, connection)

    # Act
    with caplog.at_level(logging.ERROR):
        matches = await _repository().find_nearest(EMBEDDING, FINGERPRINT)

    # Assert
    assert matches == []
    assert "Failed to read semantic cache" in caplog.text


@pytest.mark.asyncio
async def test_should_save_every_column_with_response_as_json_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    connection = FakeConnection()
    _patch_connection(monkeypatch, connection)

    # Act
    await _repository().save(_entry())

    # Assert
    _, params = connection.executed[0]
    assert params == {
        "id": ENTRY_ID,
        "prompt_version": "1.0.0",
        "rules_version": "2.0.0",
        "model_capability": "economic",
        "input_text": QUESTION,
        "normalized_text": "onde posso comprar marmitas?",
        "response_json": json.dumps(ANSWER),
        "embedding": "[0.1,0.2,-0.3]",
        "created_at": CREATED_AT,
    }
    assert json.loads(params["response_json"]) == ANSWER


@pytest.mark.asyncio
async def test_should_only_log_when_save_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    connection = FakeConnection()
    connection.error = psycopg.OperationalError("server closed the connection")
    _patch_connection(monkeypatch, connection)

    # Act
    with caplog.at_level(logging.ERROR):
        await _repository().save(_entry())

    # Assert
    assert "Failed to write semantic cache (id='12345678')" in caplog.text


@pytest.mark.asyncio
async def test_should_not_log_question_answer_or_embedding(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Arrange
    _patch_connection(monkeypatch, FakeConnection([_row(QUESTION, ANSWER, 0.1)]))
    repository = _repository()

    # Act
    with caplog.at_level(logging.DEBUG):
        await repository.find_nearest(EMBEDDING, FINGERPRINT)
        await repository.save(_entry())

    # Assert
    assert caplog.records
    for sensitive in (QUESTION, ANSWER, FINGERPRINT.normalized_text, "0.1,0.2"):
        assert sensitive not in caplog.text
