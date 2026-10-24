"""Integration tests for the client storage repository with a fake S3 client.

No real S3 calls are made: a hand-written in-memory fake keeps object bytes in a
dict and mimics the boto3 ``get_object``/``put_object`` contract (including the
``NoSuchKey`` error on a first read) so the full repository flow (create, update
and replace of JSONL records) is exercised end to end.
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
    CLIENT_RECORDS_OBJECT_KEY,
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


def _stored_records(client: _FakeS3Client) -> list[dict]:
    payload = client.store[CLIENT_RECORDS_OBJECT_KEY].decode("utf-8")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_should_persist_first_client_as_jsonl() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Padaria Central"))

    # Assert
    records = _stored_records(client)
    assert len(records) == 1
    assert records[0]["user_code"] == "123"
    assert records[0]["request"]["name"] == "Padaria Central"


@pytest.mark.asyncio
async def test_should_accumulate_records_for_distinct_clients() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Padaria"))
    await repository.save_client(_registration("456", "Floricultura"))

    # Assert
    records = _stored_records(client)
    assert {record["user_code"] for record in records} == {"123", "456"}


@pytest.mark.asyncio
async def test_should_replace_record_on_client_update() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Nome Antigo"))

    # Act
    await repository.save_client(_registration("123", "Nome Novo"))

    # Assert
    records = _stored_records(client)
    assert len(records) == 1
    assert records[0]["request"]["name"] == "Nome Novo"


@pytest.mark.asyncio
async def test_should_remove_only_deleted_client_record() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"))
    await repository.save_client(_registration("456", "Floricultura"))

    # Act
    await repository.delete_client("123")

    # Assert
    records = _stored_records(client)
    assert [record["user_code"] for record in records] == ["456"]


@pytest.mark.asyncio
async def test_should_be_idempotent_when_deleting_twice() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"))

    # Act
    await repository.delete_client("123")
    await repository.delete_client("123")

    # Assert
    assert _stored_records(client) == []


@pytest.mark.asyncio
async def test_should_allow_saving_again_after_deleting_last_record() -> None:
    # Arrange
    client = _FakeS3Client()
    repository = ClientStorageRepository(client=client, config=_config())
    await repository.save_client(_registration("123", "Padaria"))
    await repository.delete_client("123")

    # Act
    await repository.save_client(_registration("789", "Mercado"))

    # Assert
    assert [record["user_code"] for record in _stored_records(client)] == ["789"]


@pytest.mark.asyncio
async def test_should_build_real_client_without_network_call() -> None:
    # Act
    client = create_s3_client(_config())

    # Assert
    assert isinstance(client, BaseClient)
