"""Integration tests for the client storage repository with a fake S3 client.

No real S3 calls are made: a hand-written in-memory fake keeps object bytes in a
dict and mimics the boto3 ``get_object``/``put_object`` contract (including the
``NoSuchKey`` error on a first read) so the full repository flow (create, update
and replace of JSONL records, one object per category) is exercised end to end.
"""

import io
import json

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from pydantic import SecretStr

from app.domain import CompanyRegistrationRequest
from app.infrastructure.config import BucketConfig
from app.infrastructure.storage import (
    ClientStorageRepository,
    create_s3_client,
)


class _FakeS3Client:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[Key])}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **_: object) -> None:
        self.store[Key] = Body


def _config() -> BucketConfig:
    return BucketConfig(
        name="tnn-rag",
        access_key=SecretStr("access"),
        secret_key=SecretStr("secret"),
        region="us-east-1",
        host="http://localhost:5151",
        bucket_name="acha-local",
    )


def _registration(user_code: str, name: str) -> CompanyRegistrationRequest:
    return CompanyRegistrationRequest(
        user_code=user_code,
        request={
            "name": name,
            "descricao": "desc",
            "email": "shop@example.com",
            "address": "rua a",
            "telephone": "1199999",
            "detalhes": "detalhes",
        },
    )


def _stored_records(
    client: _FakeS3Client, key: str = "client_services_alimentacao.jsonl"
) -> list[dict]:
    payload = client.store[key].decode("utf-8")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_should_replace_record_on_client_update() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Nome Antigo"), "alimentacao")

    # Act
    await repository.save_client(_registration("123", "Nome Novo"), "alimentacao")

    # Assert
    records = _stored_records(client)
    assert len(records) == 1
    assert records[0]["request"]["name"] == "Nome Novo"


@pytest.mark.asyncio
async def test_should_remove_only_deleted_client_record() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")
    await repository.save_client(_registration("456", "Floricultura"), "alimentacao")

    # Act
    await repository.delete_client("123", "alimentacao")

    # Assert
    records = _stored_records(client)
    assert [record["user_code"] for record in records] == ["456"]


@pytest.mark.asyncio
async def test_should_be_idempotent_when_deleting_twice() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")

    # Act
    await repository.delete_client("123", "alimentacao")
    await repository.delete_client("123", "alimentacao")

    # Assert
    assert _stored_records(client) == []


@pytest.mark.asyncio
async def test_should_allow_saving_again_after_deleting_last_record() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")
    await repository.delete_client("123", "alimentacao")

    # Act
    await repository.save_client(_registration("789", "Mercado"), "alimentacao")

    # Assert
    assert [record["user_code"] for record in _stored_records(client)] == ["789"]


@pytest.mark.asyncio
async def test_should_keep_each_client_in_its_category_object() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")
    await repository.save_client(_registration("456", "Salao"), "beleza")

    # Assert
    assert set(client.store) == {
        "client_services_alimentacao.jsonl",
        "client_services_beleza.jsonl",
    }
    food = _stored_records(client, "client_services_alimentacao.jsonl")
    beauty = _stored_records(client, "client_services_beleza.jsonl")
    assert [record["user_code"] for record in food] == ["123"]
    assert [record["user_code"] for record in beauty] == ["456"]


@pytest.mark.asyncio
async def test_should_delete_from_one_category_without_affecting_another() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")
    await repository.save_client(_registration("456", "Salao"), "beleza")
    beauty_before = client.store["client_services_beleza.jsonl"]

    # Act
    await repository.delete_client("123", "alimentacao")
    await repository.delete_client("456", "alimentacao")

    # Assert
    assert _stored_records(client, "client_services_alimentacao.jsonl") == []
    assert client.store["client_services_beleza.jsonl"] == beauty_before


@pytest.mark.asyncio
async def test_should_never_touch_the_legacy_object() -> None:
    # Arrange
    client = _FakeS3Client()
    legacy = b'{"user_code": "123"}\n'
    client.store["client_services.jsonl"] = legacy
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")
    await repository.delete_client("123", "alimentacao")

    # Assert
    assert client.store["client_services.jsonl"] == legacy


@pytest.mark.asyncio
async def test_should_build_real_client_without_network_call() -> None:
    # Act
    client = create_s3_client(_config())

    # Assert
    assert isinstance(client, BaseClient)
