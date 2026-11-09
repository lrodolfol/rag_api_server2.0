"""Integration tests for the Pinecone repository with a fake SDK client.

No real Pinecone calls are made: a hand-written fake client keeps an in-memory
index and computes cosine similarity so the full repository flow (index
creation, delete-before-upsert replacement, category filter and lookup, query
and threshold filtering) is exercised end to end.
"""

import math
from types import SimpleNamespace

import pytest
from pinecone import Pinecone
from pydantic import SecretStr

from app.domain import EmbeddingRecord
from app.infrastructure.config import PineconeConfig
from app.infrastructure.pinecone import (
    PineconeVectorRepository,
    create_pinecone_client,
)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _matches_filter(metadata: dict, metadata_filter: dict | None) -> bool:
    """Apply the subset of Pinecone filters used by the repository."""
    for key, condition in (metadata_filter or {}).items():
        expected = condition["$eq"] if isinstance(condition, dict) else condition
        if metadata.get(key) != expected:
            return False
    return True


class _FakeIndex:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def delete(self, *, filter: dict | None = None) -> None:
        if not filter:
            return
        user_code = filter.get("user_code")
        self.store = {
            vector_id: payload
            for vector_id, payload in self.store.items()
            if payload["metadata"].get("user_code") != user_code
        }

    def upsert(self, *, vectors: list) -> None:
        for vector_id, values, metadata in vectors:
            self.store[vector_id] = {"values": values, "metadata": metadata}

    def query(
        self,
        *,
        vector: list[float],
        top_k: int,
        include_metadata: bool,
        filter: dict | None = None,
    ):
        scored = [
            SimpleNamespace(
                id=vector_id,
                score=_cosine_similarity(vector, payload["values"]),
                metadata=payload["metadata"] if include_metadata else None,
            )
            for vector_id, payload in self.store.items()
            if _matches_filter(payload["metadata"], filter)
        ]
        scored.sort(key=lambda match: match.score, reverse=True)
        return SimpleNamespace(matches=scored[:top_k])


class _FakeClient:
    def __init__(self) -> None:
        self._index = _FakeIndex()
        self.created = False

    def has_index(self, name: str) -> bool:
        return self.created

    def create_index(self, **kwargs) -> None:
        self.created = True

    def Index(self, name: str) -> _FakeIndex:
        return self._index


def _config() -> PineconeConfig:
    return PineconeConfig(
        api_key=SecretStr("integration-key"),
        index_name="acha-local-services-dev",
        region="us-east-1",
        environment="development",
        metric="cosine",
        vector_type="dense",
        dimension=2,
    )


@pytest.mark.asyncio
async def test_should_create_index_on_first_use_only() -> None:
    # Arrange
    client = _FakeClient()
    repository = PineconeVectorRepository(client=client, config=_config())

    # Act
    await repository.create_index_if_not_exists()
    await repository.create_index_if_not_exists()

    # Assert
    assert client.created is True


@pytest.mark.asyncio
async def test_should_store_and_return_only_similar_matches() -> None:
    # Arrange
    client = _FakeClient()
    repository = PineconeVectorRepository(client=client, config=_config())
    embeddings = [
        EmbeddingRecord(text="padaria", vector=[1.0, 0.0]),
        EmbeddingRecord(text="floricultura", vector=[0.0, 1.0]),
    ]
    await repository.upsert_company_vectors(
        "Padaria Central", "123", "alimentacao", embeddings
    )

    # Act
    results = await repository.query([1.0, 0.02], top_k=5)

    # Assert
    assert [match.text for match in results] == ["padaria"]
    assert results[0].score > 0.9
    assert results[0].user_code == "123"


@pytest.mark.asyncio
async def test_should_replace_previous_vectors_on_update() -> None:
    # Arrange
    client = _FakeClient()
    repository = PineconeVectorRepository(client=client, config=_config())
    await repository.upsert_company_vectors(
        "Padaria Central", "123", "alimentacao",
        [EmbeddingRecord(text="antigo", vector=[1.0, 0.0])]
    )

    # Act
    await repository.upsert_company_vectors(
        "Padaria Central", "123", "alimentacao",
        [EmbeddingRecord(text="novo", vector=[1.0, 0.0])]
    )
    results = await repository.query([1.0, 0.0], top_k=5)

    # Assert
    assert [match.text for match in results] == ["novo"]


@pytest.mark.asyncio
async def test_should_check_existence_then_delete_only_target_user_code() -> None:
    # Arrange
    client = _FakeClient()
    repository = PineconeVectorRepository(client=client, config=_config())
    await repository.upsert_company_vectors(
        "Padaria", "123", "alimentacao",
        [EmbeddingRecord(text="padaria", vector=[1.0, 0.0])]
    )
    await repository.upsert_company_vectors(
        "Floricultura", "456", "alimentacao",
        [EmbeddingRecord(text="flores", vector=[0.0, 1.0])]
    )

    # Act
    found_before = await repository.has_vectors_for_user_code("123")
    await repository.delete_by_user_code("123")
    found_after = await repository.has_vectors_for_user_code("123")

    # Assert
    assert found_before is True
    assert found_after is False
    assert await repository.has_vectors_for_user_code("456") is True


async def _two_categories_repository() -> PineconeVectorRepository:
    repository = PineconeVectorRepository(client=_FakeClient(), config=_config())
    await repository.upsert_company_vectors(
        "Padaria", "123", "alimentacao", [EmbeddingRecord(text="padaria", vector=[1.0, 0.0])]
    )
    await repository.upsert_company_vectors(
        "Clinica", "456", "saude", [EmbeddingRecord(text="clinica", vector=[1.0, 0.1])]
    )
    return repository


@pytest.mark.asyncio
async def test_should_return_only_vectors_of_the_filtered_category() -> None:
    # Arrange
    repository = await _two_categories_repository()

    # Act
    food = await repository.query([1.0, 0.0], top_k=5, category_slug="alimentacao")
    health = await repository.query([1.0, 0.0], top_k=5, category_slug="saude")
    other = await repository.query([1.0, 0.0], top_k=5, category_slug="moda")
    unfiltered = await repository.query([1.0, 0.0], top_k=5)

    # Assert
    assert [(match.text, match.category) for match in food] == [("padaria", "alimentacao")]
    assert [(match.text, match.category) for match in health] == [("clinica", "saude")]
    assert other == []
    assert {match.text for match in unfiltered} == {"padaria", "clinica"}


@pytest.mark.asyncio
async def test_should_read_category_by_user_code() -> None:
    # Arrange
    repository = await _two_categories_repository()

    # Act / Assert
    assert await repository.get_category_by_user_code("123") == "alimentacao"
    assert await repository.get_category_by_user_code("456") == "saude"
    assert await repository.get_category_by_user_code("unknown") is None


@pytest.mark.asyncio
async def test_should_read_new_category_after_client_changes_category() -> None:
    # Arrange
    repository = await _two_categories_repository()

    # Act
    await repository.upsert_company_vectors(
        "Padaria", "123", "comercio", [EmbeddingRecord(text="mercearia", vector=[1.0, 0.0])]
    )

    # Assert
    assert await repository.get_category_by_user_code("123") == "comercio"
    assert await repository.query([1.0, 0.0], top_k=5, category_slug="alimentacao") == []


@pytest.mark.asyncio
async def test_should_return_no_category_for_legacy_vectors() -> None:
    # Arrange
    client = _FakeClient()
    repository = PineconeVectorRepository(client=client, config=_config())
    await repository.create_index_if_not_exists()
    client.Index("any").upsert(vectors=[("old-1", [1.0, 0.0], {"text": "a", "user_code": "789"})])

    # Act / Assert
    assert await repository.has_vectors_for_user_code("789") is True
    assert await repository.get_category_by_user_code("789") is None


@pytest.mark.asyncio
async def test_should_build_real_client_without_network_call() -> None:
    # Act
    client = create_pinecone_client(_config())

    # Assert
    assert isinstance(client, Pinecone)
