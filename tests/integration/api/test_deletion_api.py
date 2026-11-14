"""Integration tests for the company deletion endpoint.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the
deletion service is replaced with a fake via dependency override so no external
provider is contacted.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from httpx import Response
from redis.exceptions import RedisError

from app.api.dependencies import get_deletion_service
from app.application.cache import SemanticCacheService
from app.application.deletion import DeletionService
from app.domain import (
    ClientStorageError,
    CompanyDeletionRequest,
    DomainError,
    VectorRepositoryError,
)
from app.infrastructure.config import PostgresConfig, SemanticCacheConfig
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.redis import RedisAnswerCacheRepository
from app.main import create_app


class _FakeDeletionService:
    """In-memory stand-in recording deletions and optionally failing them."""

    def __init__(self, *, error: DomainError | None = None) -> None:
        self._error = error
        self.calls: list[CompanyDeletionRequest] = []

    async def delete(self, request: CompanyDeletionRequest) -> None:
        self.calls.append(request)
        if self._error:
            raise self._error


def _delete(service: _FakeDeletionService, payload: dict | None) -> Response:
    app = create_app()
    app.dependency_overrides[get_deletion_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)
    return client.request("DELETE", "/companies", json=payload)


def test_should_delete_company_and_return_ok_envelope() -> None:
    # Arrange
    service = _FakeDeletionService()

    # Act
    response = _delete(service, {"user_code": "rodolfo12301"})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == 200
    assert body["errors"] == []
    assert [call.user_code for call in service.calls] == ["rodolfo12301"]


@pytest.mark.parametrize("payload", [None, {}, {"user_code": ""}])
def test_should_reject_invalid_payload_with_validation_error(payload: dict | None) -> None:
    # Arrange
    service = _FakeDeletionService()

    # Act
    response = _delete(service, payload)

    # Assert
    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    "error",
    [
        VectorRepositoryError("Failed to delete vectors"),
        ClientStorageError("Failed to persist client record"),
    ],
)
def test_should_return_safe_internal_error_envelope(error: DomainError) -> None:
    # Arrange
    service = _FakeDeletionService(error=error)

    # Act
    response = _delete(service, {"user_code": "123"})

    # Assert
    assert response.status_code == 500
    body = response.json()
    assert body["status_code"] == 500
    assert body["errors"] == ["internal_error"]
    assert str(error) not in body["message"]


# --- Real deletion service: category passed to storage ----------------------


def _real_deletion_client(
    redis_client: Any = None,
) -> tuple[TestClient, AsyncMock, AsyncMock]:
    """Real deletion service for a client with vectors in ``beleza``."""
    vectors = AsyncMock()
    vectors.has_vectors_for_user_code.return_value = True
    vectors.get_category_by_user_code.return_value = "beleza"
    storage = AsyncMock()
    postgres = PostgresConfig(
        host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
    )
    cache = SemanticCacheService(
        PostgresSemanticCacheRepository(
            postgres, SemanticCacheConfig(table="rag_response_cache", top_k=3)
        )
    )
    answer_cache = RedisAnswerCacheRepository(
        redis_client or FakeAsyncRedis(decode_responses=True)
    )
    service = DeletionService(vectors, storage, cache, answer_cache)
    app = create_app()
    app.dependency_overrides[get_deletion_service] = lambda: service
    return TestClient(app), vectors, storage


def test_should_return_200_when_cache_invalidation_fails(semantic_cache_db: Any) -> None:
    # Arrange: the client has vectors, but PostgreSQL is down during invalidation.
    semantic_cache_db.error = psycopg.OperationalError("db down")
    client, vectors, storage = _real_deletion_client()

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert
    assert response.status_code == 200
    vectors.delete_by_user_code.assert_awaited_once_with("123")
    storage.delete_client.assert_awaited_once_with("123", "beleza")


def test_should_return_200_when_redis_invalidation_fails(semantic_cache_db: Any) -> None:
    # Arrange: the client has vectors, but Redis is down during invalidation.
    redis_client = MagicMock()
    redis_client.smembers = AsyncMock(side_effect=RedisError("redis down"))
    client, vectors, storage = _real_deletion_client(redis_client)

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert
    assert response.status_code == 200
    vectors.delete_by_user_code.assert_awaited_once_with("123")
    storage.delete_client.assert_awaited_once_with("123", "beleza")
