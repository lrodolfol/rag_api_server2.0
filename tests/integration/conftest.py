"""Shared integration fixtures.

``semantic_cache_db`` replaces the psycopg connection used by
:class:`PostgresSemanticCacheRepository` with an in-memory database that keeps
inserted rows, answers the nearest-neighbour query by computing the cosine
distance in Python, mimicking pgvector, and applies the delete-by-category
statement (category match or ``NULL`` category). Setting ``error`` simulates a
database failure on every statement.
"""

import json
import math
from typing import Any, Self

import psycopg
import pytest
from psycopg import sql

from app.infrastructure.config import PostgresConfig
from app.infrastructure.postgres import semantic_cache_repository

FINGERPRINT_COLUMNS = ("prompt_version", "rules_version", "model_capability")


def _parse_vector(literal: str) -> list[float]:
    return [float(value) for value in literal.strip("[]").split(",")]


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return 1 - dot / norm


class InMemorySemanticCacheDatabase:
    """Stores inserted rows and answers the nearest-neighbour query."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self.statements: list[str] = []
        self.last_result: list[dict[str, Any]] = []
        self.rowcount: int = 0
        self.error: psycopg.Error | None = None

    @property
    def select_count(self) -> int:
        return sum(1 for statement in self.statements if "SELECT" in statement)

    def execute(self, query: sql.Composed, params: dict[str, Any]) -> None:
        if self.error is not None:
            raise self.error
        statement = query.as_string(None)
        self.statements.append(statement)
        if statement.lstrip().startswith("INSERT"):
            self.rows.append(dict(params))
            self.rowcount = 1
        elif statement.lstrip().startswith("DELETE"):
            self.rowcount = self._delete_by_category(params["category"])
        else:
            self.last_result = self._nearest(params)

    def _delete_by_category(self, category: str | None) -> int:
        kept = [
            row
            for row in self.rows
            if row.get("category") is not None and row.get("category") != category
        ]
        deleted = len(self.rows) - len(kept)
        self.rows = kept
        return deleted

    def _nearest(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        query_vector = _parse_vector(params["embedding"])
        candidates = [
            row
            for row in self.rows
            if all(row[key] == params[key] for key in FINGERPRINT_COLUMNS)
        ]
        results = [self._to_result(row, query_vector) for row in candidates]
        results.sort(key=lambda result: result["distance"])
        return results[: params["limit"]]

    @staticmethod
    def _to_result(row: dict[str, Any], query_vector: list[float]) -> dict[str, Any]:
        distance = _cosine_distance(_parse_vector(row["embedding"]), query_vector)
        return {
            "input_text": row["input_text"],
            # psycopg decodes JSONB into the Python value (here, the answer text).
            "response_json": json.loads(row["response_json"]),
            "distance": distance,
            "similarity": 1 - distance,
            "category": row["category"],
        }


class _FakeCursor:
    def __init__(self, database: InMemorySemanticCacheDatabase) -> None:
        self._database = database

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    @property
    def rowcount(self) -> int:
        return self._database.rowcount

    async def execute(self, query: sql.Composed, params: dict[str, Any]) -> None:
        self._database.execute(query, params)

    async def fetchall(self) -> list[dict[str, Any]]:
        return self._database.last_result


class _FakeConnection:
    def __init__(self, database: InMemorySemanticCacheDatabase) -> None:
        self._database = database

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def cursor(self, row_factory: Any = None) -> _FakeCursor:
        return _FakeCursor(self._database)

    async def execute(self, query: sql.Composed, params: dict[str, Any]) -> _FakeCursor:
        self._database.execute(query, params)
        return _FakeCursor(self._database)


@pytest.fixture
def semantic_cache_db(monkeypatch: pytest.MonkeyPatch) -> InMemorySemanticCacheDatabase:
    """Route every semantic cache connection to a fresh in-memory database."""
    database = InMemorySemanticCacheDatabase()

    async def _open(_: PostgresConfig) -> _FakeConnection:
        return _FakeConnection(database)

    monkeypatch.setattr(semantic_cache_repository, "open_postgres_connection", _open)
    return database
