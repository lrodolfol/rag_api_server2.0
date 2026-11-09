"""Unit tests for :class:`ClientStorageRepository` using a mocked S3 client."""

import io
import json
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import SecretStr

from app.domain import ClientStorageError, CompanyRegistrationRequest
from app.infrastructure.config import BucketConfig
from app.infrastructure.storage import (
    ClientStorageRepository,
)


def _config(bucket_name: str | None = "acha-local") -> BucketConfig:
    return BucketConfig(
        name="tnn-rag",
        access_key=SecretStr("access"),
        secret_key=SecretStr("secret"),
        region="us-east-1",
        host="http://localhost:5151",
        bucket_name=bucket_name,
    )


def _registration(user_code: str = "123", name: str = "Padaria") -> CompanyRegistrationRequest:
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


def _missing_object_error() -> ClientError:
    return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


def _client_with_body(payload: bytes | None) -> MagicMock:
    client = MagicMock()
    if payload is None:
        client.get_object.side_effect = _missing_object_error()
    else:
        client.get_object.return_value = {"Body": io.BytesIO(payload)}
    return client


def _written_records(client: MagicMock) -> list[dict]:
    body = client.put_object.call_args.kwargs["Body"].decode("utf-8")
    return [json.loads(line) for line in body.splitlines() if line.strip()]


@pytest.mark.asyncio
async def test_should_write_single_record_when_object_missing() -> None:
    # Arrange
    client = _client_with_body(None)
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Padaria"), "alimentacao")

    # Assert
    kwargs = client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "acha-local"
    assert kwargs["Key"] == "client_services_alimentacao.jsonl"
    assert client.get_object.call_args.kwargs["Key"] == "client_services_alimentacao.jsonl"
    records = _written_records(client)
    assert len(records) == 1
    assert records[0]["user_code"] == "123"
    assert records[0]["request"]["name"] == "Padaria"


@pytest.mark.asyncio
async def test_should_replace_record_for_existing_user_code() -> None:
    # Arrange
    old = json.dumps(_registration("123", "Nome Antigo").model_dump(mode="json"))
    other = json.dumps(_registration("999", "Outro").model_dump(mode="json"))
    client = _client_with_body((old + "\n" + other + "\n").encode("utf-8"))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("123", "Nome Novo"), "alimentacao")

    # Assert
    records = _written_records(client)
    assert [record["user_code"] for record in records] == ["999", "123"]
    updated = next(record for record in records if record["user_code"] == "123")
    assert updated["request"]["name"] == "Nome Novo"


@pytest.mark.asyncio
async def test_should_serialize_each_record_on_its_own_line() -> None:
    # Arrange
    existing = json.dumps(_registration("111", "Floricultura").model_dump(mode="json"))
    client = _client_with_body((existing + "\n").encode("utf-8"))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("222", "Padaria"), "alimentacao")

    # Assert
    body = client.put_object.call_args.kwargs["Body"].decode("utf-8")
    assert body.endswith("\n")
    assert len([line for line in body.splitlines() if line.strip()]) == 2


@pytest.mark.asyncio
async def test_should_raise_when_bucket_name_missing() -> None:
    # Arrange
    client = MagicMock()
    repository = ClientStorageRepository(client=client, config=_config(bucket_name=None))

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await repository.save_client(_registration(), "alimentacao")
    client.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_read() -> None:
    # Arrange
    client = MagicMock()
    client.get_object.side_effect = BotoCoreError()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await repository.save_client(_registration(), "alimentacao")
    client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_write() -> None:
    # Arrange
    client = _client_with_body(None)
    client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied"}}, "PutObject"
    )
    repository = ClientStorageRepository(client=client, config=_config())

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await repository.save_client(_registration(), "alimentacao")


def _jsonl(*registrations: CompanyRegistrationRequest) -> bytes:
    lines = [json.dumps(item.model_dump(mode="json")) for item in registrations]
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.asyncio
async def test_should_delete_only_target_user_code_record() -> None:
    # Arrange
    payload = _jsonl(_registration("111", "Floricultura"), _registration("222", "Padaria"))
    client = _client_with_body(payload)
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.delete_client("111", "alimentacao")

    # Assert
    records = _written_records(client)
    assert [record["user_code"] for record in records] == ["222"]


@pytest.mark.asyncio
async def test_should_not_rewrite_when_user_code_not_found_on_delete() -> None:
    # Arrange
    client = _client_with_body(_jsonl(_registration("111", "Floricultura")))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.delete_client("999", "alimentacao")

    # Assert
    client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_not_rewrite_when_object_missing_on_delete() -> None:
    # Arrange
    client = _client_with_body(None)
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.delete_client("111", "alimentacao")

    # Assert
    client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_wrap_provider_error_on_delete() -> None:
    # Arrange
    client = MagicMock()
    client.get_object.side_effect = BotoCoreError()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await repository.delete_client("111", "alimentacao")
    client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_not_log_user_code_on_delete(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    client = _client_with_body(_jsonl(_registration("secret-code", "Padaria")))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    with caplog.at_level("INFO"):
        await repository.delete_client("secret-code", "alimentacao")

    # Assert
    assert "secret-code" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("category_slug", "expected_key"),
    [
        ("alimentacao", "client_services_alimentacao.jsonl"),
        ("servicos_profissionais", "client_services_servicos_profissionais.jsonl"),
    ],
)
async def test_should_read_and_write_only_the_category_object(
    category_slug: str, expected_key: str
) -> None:
    # Arrange
    client = _client_with_body(_jsonl(_registration("111", "Floricultura")))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.save_client(_registration("222", "Padaria"), category_slug)

    # Assert
    client.get_object.assert_called_once_with(Bucket="acha-local", Key=expected_key)
    assert client.put_object.call_args.kwargs["Key"] == expected_key
    assert [record["user_code"] for record in _written_records(client)] == ["111", "222"]


@pytest.mark.asyncio
async def test_should_delete_from_the_category_object() -> None:
    # Arrange
    client = _client_with_body(_jsonl(_registration("111", "Salao")))
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    await repository.delete_client("111", "beleza")

    # Assert
    client.get_object.assert_called_once_with(
        Bucket="acha-local", Key="client_services_beleza.jsonl"
    )
    assert client.put_object.call_args.kwargs["Key"] == "client_services_beleza.jsonl"
    assert client.put_object.call_args.kwargs["Body"] == b""


@pytest.mark.asyncio
@pytest.mark.parametrize("category_slug", ["", "   "])
async def test_should_reject_blank_category_slug_without_calling_s3(
    category_slug: str,
) -> None:
    # Arrange
    client = MagicMock()
    repository = ClientStorageRepository(client=client, config=_config())

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await repository.save_client(_registration(), category_slug)
    with pytest.raises(ClientStorageError):
        await repository.delete_client("111", category_slug)
    client.get_object.assert_not_called()
    client.put_object.assert_not_called()


@pytest.mark.asyncio
async def test_should_log_object_key_with_category(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    client = _client_with_body(None)
    repository = ClientStorageRepository(client=client, config=_config())

    # Act
    with caplog.at_level("INFO"):
        await repository.save_client(_registration("secret-code", "Padaria"), "moda")

    # Assert
    assert "client_services_moda.jsonl" in caplog.text
    assert "secret-code" not in caplog.text
