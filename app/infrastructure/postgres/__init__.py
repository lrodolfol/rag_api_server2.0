"""PostgreSQL integration package.

Exposes the async semantic-cache repository (pgvector) and the factory that
opens a connection from the typed configuration.
"""

from app.infrastructure.postgres.client import open_postgres_connection
from app.infrastructure.postgres.semantic_cache_repository import (
    PostgresSemanticCacheRepository,
)

__all__ = [
    "PostgresSemanticCacheRepository",
    "open_postgres_connection",
]
