"""Integration tests for :class:`DeletionService` with real repositories.

No real Pinecone or S3 calls are made: minimal in-memory fakes mimic the SDK
contracts used by the repositories, so the whole deletion flow (existence check,
category lookup, vector delete and removal from the category JSONL object) is
exercised end to end.
"""

import io
import json
from types import SimpleNamespace
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fakeredis import FakeAsyncRedis
from pydantic import SecretStr

from app.application.cache import SemanticCacheService
from app.application.deletion import DeletionService
from app.domain import (
    CompanyDeletionRequest,
    CompanyRegistrationRequest,
    EmbeddingRecord,
)
from app.infrastructure.config import (
    BucketConfig,
    PineconeConfig,
    PostgresConfig,
    SemanticCacheConfig,
)
from app.infrastructure.pinecone import PineconeVectorRepository
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.redis import RedisAnswerCacheRepository
from app.infrastructure.storage import (
    CLIENT_RECORDS_OBJECT_KEY_TEMPLATE,
    ClientStorageRepository,
)

FOOD_KEY = "f" * 64
BEAUTY_KEY = "e" * 64
UNCATEGORIZED_KEY = "c" * 64


class _FakeIndex:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def delete(self, *, filter: dict) -> None:
        self.store = {
            key: value
            for key, value in self.store.items()
            if value["user_code"] != filter["user_code"]
        }

    def upsert(self, *, vectors: list) -> None:
        for vector_id, _, metadata in vectors:
            self.store[vector_id] = metadata

    def query(
        self, *, filter: dict, top_k: int, include_metadata: bool, **_: object
    ) -> SimpleNamespace:
        matches = [
            SimpleNamespace(id=key, metadata=value if include_metadata else None)
            for key, value in self.store.items()
            if value["user_code"] == filter["user_code"]
        ]
        return SimpleNamespace(matches=matches[:top_k])


class _FakePinecone:
    def __init__(self) -> None:
        self.index = _FakeIndex()

    def has_index(self, name: str) -> bool:
        return True

    def Index(self, name: str) -> _FakeIndex:
        return self.index


class _FakeS3Client:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[Key])}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **_: object) -> None:
        self.store[Key] = Body


def _pinecone_config() -> PineconeConfig:
    return PineconeConfig(
        api_key=SecretStr("integration-key"),
        index_name="acha-local-services-dev",
        region="us-east-1",
        environment="development",
        metric="cosine",
        vector_type="dense",
        dimension=2,
    )


def _bucket_config() -> BucketConfig:
    return BucketConfig(
        name="tnn-rag",
        access_key=SecretStr("access"),
        secret_key=SecretStr("secret"),
        region="us-east-1",
        host="http://localhost:5151",
        bucket_name="acha-local",
    )


def _registration(user_code: str) -> CompanyRegistrationRequest:
    return CompanyRegistrationRequest(
        user_code=user_code,
        request={
            "name": "Padaria",
            "descricao": "desc",
            "email": "shop@example.com",
            "address": "rua a",
            "telephone": "1199999",
            "detalhes": "detalhes",
        },
    )


async def _build(
    *clients: tuple[str, str],
    answer_cache: RedisAnswerCacheRepository | None = None,
) -> tuple[DeletionService, PineconeVectorRepository, _FakeS3Client]:
    """Register each ``(user_code, category_slug)`` in the vectors and storage."""
    s3 = _FakeS3Client()
    vectors = PineconeVectorRepository(client=_FakePinecone(), config=_pinecone_config())
    storage = ClientStorageRepository(client=s3, config=_bucket_config())
    for user_code, category_slug in clients:
        embeddings = [EmbeddingRecord(text="padaria", vector=[1.0, 0.0])]
        await vectors.upsert_company_vectors("Padaria", user_code, category_slug, embeddings)
        await storage.save_client(_registration(user_code), category_slug)
    postgres = PostgresConfig(
        host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
    )
    cache = SemanticCacheService(
        PostgresSemanticCacheRepository(
            postgres, SemanticCacheConfig(table="rag_response_cache", top_k=3)
        )
    )
    exact_cache = answer_cache or RedisAnswerCacheRepository(
        FakeAsyncRedis(decode_responses=True)
    )
    return DeletionService(vectors, storage, cache, exact_cache), vectors, s3


async def _seeded_answer_cache() -> RedisAnswerCacheRepository:
    """Exact cache holding one answer in ``beleza``, one in ``alimentacao`` and one uncategorized."""
    answer_cache = RedisAnswerCacheRepository(FakeAsyncRedis(decode_responses=True))
    await answer_cache.set(BEAUTY_KEY, "Salao", {"beleza"})
    await answer_cache.set(FOOD_KEY, "Padaria", {"alimentacao"})
    await answer_cache.set(UNCATEGORIZED_KEY, "Padaria e Salao", {None})
    return answer_cache


def _stored_user_codes(s3: _FakeS3Client, category_slug: str = "alimentacao") -> list[str]:
    key = CLIENT_RECORDS_OBJECT_KEY_TEMPLATE.format(category=category_slug)
    payload = s3.store[key].decode("utf-8")
    return [json.loads(line)["user_code"] for line in payload.splitlines() if line]


@pytest.mark.asyncio
async def test_should_remove_vectors_and_record_of_target_client_only() -> None:
    # Arrange
    service, vectors, s3 = await _build(("123", "alimentacao"), ("456", "alimentacao"))

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await vectors.has_vectors_for_user_code("123") is False
    assert await vectors.has_vectors_for_user_code("456") is True
    assert _stored_user_codes(s3) == ["456"]


@pytest.mark.asyncio
async def test_should_keep_everything_when_client_has_no_vectors() -> None:
    # Arrange
    service, vectors, s3 = await _build(("456", "alimentacao"))

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await vectors.has_vectors_for_user_code("456") is True
    assert _stored_user_codes(s3) == ["456"]


@pytest.mark.asyncio
async def test_should_remove_record_only_from_the_client_category_object() -> None:
    # Arrange
    service, vectors, s3 = await _build(("123", "beleza"), ("456", "alimentacao"))
    food_before = s3.store["client_services_alimentacao.jsonl"]

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await vectors.has_vectors_for_user_code("123") is False
    assert _stored_user_codes(s3, "beleza") == []
    assert s3.store["client_services_alimentacao.jsonl"] == food_before


@pytest.mark.asyncio
async def test_should_delete_legacy_vectors_without_touching_storage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange: vectors stored before categories existed (no ``category`` metadata).
    service, vectors, s3 = await _build(("456", "alimentacao"))
    legacy = b'{"user_code": "789"}\n'
    s3.store["client_services.jsonl"] = legacy
    index = vectors._client.Index("any")
    index.upsert(vectors=[("old-789-0", [1.0, 0.0], {"text": "a", "user_code": "789"})])
    objects_before = dict(s3.store)

    # Act
    with caplog.at_level("WARNING"):
        await service.delete(CompanyDeletionRequest(user_code="789"))

    # Assert
    assert await vectors.has_vectors_for_user_code("789") is False
    assert s3.store == objects_before
    assert "legacy record was not removed from the bucket" in caplog.text


@pytest.mark.asyncio
async def test_should_invalidate_deleted_client_category_and_uncategorized_cache_rows(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    service, _, _ = await _build(("123", "beleza"), ("456", "alimentacao"))
    semantic_cache_db.rows = [{"category": slug} for slug in ("beleza", "alimentacao", None)]

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == ["alimentacao"]


@pytest.mark.asyncio
async def test_should_not_invalidate_cache_when_client_has_no_vectors(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    service, _, _ = await _build(("456", "alimentacao"))
    semantic_cache_db.rows = [{"category": slug} for slug in ("alimentacao", None)]

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert len(semantic_cache_db.rows) == 2


@pytest.mark.asyncio
async def test_should_invalidate_deleted_client_category_and_uncategorized_exact_answers(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    answer_cache = await _seeded_answer_cache()
    service, _, _ = await _build(
        ("123", "beleza"), ("456", "alimentacao"), answer_cache=answer_cache
    )

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await answer_cache.get(BEAUTY_KEY) is None
    assert await answer_cache.get(UNCATEGORIZED_KEY) is None
    assert await answer_cache.get(FOOD_KEY) == "Padaria"


@pytest.mark.asyncio
async def test_should_invalidate_only_uncategorized_exact_answers_for_legacy_client(
    semantic_cache_db: Any,
) -> None:
    # Arrange: vectors stored before categories existed (no ``category`` metadata).
    answer_cache = await _seeded_answer_cache()
    service, vectors, _ = await _build(answer_cache=answer_cache)
    index = vectors._client.Index("any")
    index.upsert(vectors=[("old-789-0", [1.0, 0.0], {"text": "a", "user_code": "789"})])

    # Act
    await service.delete(CompanyDeletionRequest(user_code="789"))

    # Assert
    assert await answer_cache.get(UNCATEGORIZED_KEY) is None
    assert await answer_cache.get(BEAUTY_KEY) == "Salao"
    assert await answer_cache.get(FOOD_KEY) == "Padaria"


@pytest.mark.asyncio
async def test_should_not_invalidate_exact_answers_when_client_has_no_vectors(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    answer_cache = await _seeded_answer_cache()
    service, _, _ = await _build(("456", "alimentacao"), answer_cache=answer_cache)

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await answer_cache.get(BEAUTY_KEY) == "Salao"
    assert await answer_cache.get(FOOD_KEY) == "Padaria"
    assert await answer_cache.get(UNCATEGORIZED_KEY) == "Padaria e Salao"
