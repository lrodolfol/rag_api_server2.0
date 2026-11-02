"""Asynchronous PostgreSQL (pgvector) semantic-cache repository.

Finds the cached answers whose question embedding is closest (cosine distance)
to a given embedding, restricted to the same prompt/rules/model fingerprint, and
stores new answers. This is the only module that knows SQL and ``psycopg``.

Embeddings are sent in pgvector's text format (``'[0.1,0.2,...]'``) and cast
with ``::vector`` in SQL, so the Python ``pgvector`` package is not needed. The
table name is composed with :class:`psycopg.sql.Identifier`; every value is a
query parameter.

The cache is an optimisation, never a dependency of the search flow: database
failures are logged and treated as a miss (read) or ignored (write). Neither
questions, answers nor embeddings are logged.
"""

import json
from typing import Final

import psycopg
from psycopg import sql
from psycopg.rows import DictRow, dict_row
from pydantic import ValidationError

from app.domain import CacheFingerprint, SemanticCacheEntry, SemanticCacheMatch
from app.infrastructure.config import PostgresConfig, SemanticCacheConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.postgres.client import open_postgres_connection

logger = get_logger(__name__)

_LOGGED_ID_LENGTH: Final[int] = 8

FIND_NEAREST_SQL: Final[sql.SQL] = sql.SQL(
    """
    WITH query_embedding AS (
        SELECT %(embedding)s::vector AS value
    )
    SELECT c.input_text,
           c.response_json,
           c.embedding <=> q.value AS distance,
           1 - (c.embedding <=> q.value) AS similarity
    FROM {table} c
    CROSS JOIN query_embedding q
    WHERE c.prompt_version   = %(prompt_version)s
      AND c.rules_version    = %(rules_version)s
      AND c.model_capability = %(model_capability)s
    ORDER BY c.embedding <=> q.value
    LIMIT %(limit)s
    """
)

INSERT_SQL: Final[sql.SQL] = sql.SQL(
    """
    INSERT INTO {table} (
        id, prompt_version, rules_version, model_capability, input_text,
        normalized_text, response_json, embedding, created_at
    ) VALUES (
        %(id)s, %(prompt_version)s, %(rules_version)s, %(model_capability)s,
        %(input_text)s, %(normalized_text)s, %(response_json)s::jsonb,
        %(embedding)s::vector, %(created_at)s
    )
    """
)


class PostgresSemanticCacheRepository:
    """Async repository for semantically cached RAG answers kept in PostgreSQL."""

    def __init__(
        self, postgres_config: PostgresConfig, semantic_cache_config: SemanticCacheConfig
    ) -> None:
        table = sql.Identifier(semantic_cache_config.table)
        self._postgres_config = postgres_config
        self._top_k = semantic_cache_config.top_k
        self._find_nearest_query = FIND_NEAREST_SQL.format(table=table)
        self._insert_query = INSERT_SQL.format(table=table)

    async def find_nearest(
        self, embedding: list[float], fingerprint: CacheFingerprint
    ) -> list[SemanticCacheMatch]:
        """Return up to ``top_k`` matches, most similar first; ``[]`` on failure."""
        params = {
            "embedding": to_vector_literal(embedding),
            "prompt_version": fingerprint.prompt_version,
            "rules_version": fingerprint.rules_version,
            "model_capability": fingerprint.model_capability,
            "limit": self._top_k,
        }
        try:
            rows = await self._fetch_all(self._find_nearest_query, params)
            matches = [_to_match(row) for row in rows]
        except (psycopg.Error, ValidationError):
            logger.exception("Failed to read semantic cache")
            return []
        logger.info("Semantic cache lookup returned %d match(es)", len(matches))
        return matches

    async def save(self, entry: SemanticCacheEntry) -> None:
        """Persist ``entry``; failures are logged and never raised."""
        entry_id = str(entry.id)[:_LOGGED_ID_LENGTH]
        try:
            await self._execute(self._insert_query, _to_insert_params(entry))
        except psycopg.Error:
            logger.exception("Failed to write semantic cache (id='%s')", entry_id)
            return
        logger.info("Answer stored in semantic cache (id='%s')", entry_id)

    async def _fetch_all(self, query: sql.Composed, params: dict) -> list[DictRow]:
        async with await open_postgres_connection(self._postgres_config) as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()

    async def _execute(self, query: sql.Composed, params: dict) -> None:
        async with await open_postgres_connection(self._postgres_config) as connection:
            await connection.execute(query, params)


def to_vector_literal(embedding: list[float]) -> str:
    """Serialize ``embedding`` in pgvector's text format: ``'[0.1,0.2,...]'``."""
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"


def _to_match(row: DictRow) -> SemanticCacheMatch:
    return SemanticCacheMatch(
        input_text=row["input_text"],
        response=row["response_json"],
        distance=row["distance"],
        similarity=row["similarity"],
    )


def _to_insert_params(entry: SemanticCacheEntry) -> dict:
    return {
        "id": entry.id,
        "prompt_version": entry.fingerprint.prompt_version,
        "rules_version": entry.fingerprint.rules_version,
        "model_capability": entry.fingerprint.model_capability,
        "input_text": entry.input_text,
        "normalized_text": entry.fingerprint.normalized_text,
        "response_json": json.dumps(entry.response),
        "embedding": to_vector_literal(entry.embedding),
        "created_at": entry.created_at,
    }
