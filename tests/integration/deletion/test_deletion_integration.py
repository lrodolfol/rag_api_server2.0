"""Integration tests for :class:`DeletionService` with real repositories.

No real Pinecone or S3 calls are made: minimal in-memory fakes mimic the SDK
contracts used by the repositories, so the whole deletion flow (existence check,
vector delete and JSONL record removal) is exercised end to end.
"""

import io
import json
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError
from pydantic import SecretStr

from app.application.deletion import DeletionService
from app.domain import (
    CompanyDeletionRequest,
    CompanyRegistrationRequest,
    EmbeddingRecord,
)
from app.infrastructure.config import BucketConfig, PineconeConfig
from app.infrastructure.pinecone import PineconeVectorRepository
from app.infrastructure.storage import (
    CLIENT_RECORDS_OBJECT_KEY,
    ClientStorageRepository,
)


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

    def query(self, *, filter: dict, top_k: int, **_: object) -> SimpleNamespace:
        matches = [
            SimpleNamespace(id=key)
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
    *user_codes: str,
) -> tuple[DeletionService, PineconeVectorRepository, _FakeS3Client]:
    s3 = _FakeS3Client()
    vectors = PineconeVectorRepository(client=_FakePinecone(), config=_pinecone_config())
    storage = ClientStorageRepository(client=s3, config=_bucket_config())
    for user_code in user_codes:
        embeddings = [EmbeddingRecord(text="padaria", vector=[1.0, 0.0])]
        await vectors.upsert_company_vectors("Padaria", user_code, embeddings)
        await storage.save_client(_registration(user_code))
    return DeletionService(vectors, storage), vectors, s3


def _stored_user_codes(s3: _FakeS3Client) -> list[str]:
    payload = s3.store[CLIENT_RECORDS_OBJECT_KEY].decode("utf-8")
    return [json.loads(line)["user_code"] for line in payload.splitlines() if line]


@pytest.mark.asyncio
async def test_should_remove_vectors_and_record_of_target_client_only() -> None:
    # Arrange
    service, vectors, s3 = await _build("123", "456")

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await vectors.has_vectors_for_user_code("123") is False
    assert await vectors.has_vectors_for_user_code("456") is True
    assert _stored_user_codes(s3) == ["456"]


@pytest.mark.asyncio
async def test_should_keep_everything_when_client_has_no_vectors() -> None:
    # Arrange
    service, vectors, s3 = await _build("456")

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    assert await vectors.has_vectors_for_user_code("456") is True
    assert _stored_user_codes(s3) == ["456"]
