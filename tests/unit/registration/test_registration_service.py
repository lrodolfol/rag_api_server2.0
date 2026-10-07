"""Unit tests for :class:`RegistrationService` with mocked dependencies."""

from unittest.mock import AsyncMock

import pytest

from app.application.registration import RegistrationService
from app.domain import (
    CompanyRegistrationRequest,
    EmbeddingRecord,
    InappropriateContentError,
)
from app.infrastructure.openai import ModerationResult

Mocks = tuple[RegistrationService, AsyncMock, AsyncMock, AsyncMock]


def _registration(
    user_code: str = "123", name: str = "Padaria"
) -> CompanyRegistrationRequest:
    return CompanyRegistrationRequest(
        user_code=user_code,
        request={
            "name": name,
            "descricao": "bolos e paes",
            "email": "shop@example.com",
            "address": "rua a, 10",
            "telephone": "1199999",
            "detalhes": "Horario: 8h-18h",
        },
    )


def _service(
    *, insult: bool = False, embeddings: list[EmbeddingRecord] | None = None
) -> Mocks:
    openai = AsyncMock()
    openai.moderate.return_value = ModerationResult(insult=insult, insult_text="")
    openai.generate_embeddings_from_chunks.return_value = (
        embeddings
        if embeddings is not None
        else [EmbeddingRecord(text="bolos", vector=[0.1, 0.2])]
    )
    vectors = AsyncMock()
    storage = AsyncMock()
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
    )
    return service, openai, vectors, storage


@pytest.mark.asyncio
async def test_should_persist_vectors_and_save_client_on_valid_registration() -> None:
    # Arrange
    service, openai, vectors, storage = _service()
    registration = _registration("123", "Padaria")

    # Act
    await service.register(registration)

    # Assert
    openai.moderate.assert_awaited_once()
    upsert_args = vectors.upsert_company_vectors.await_args.args
    assert upsert_args[0] == "Padaria"
    assert upsert_args[1] == "123"
    storage.save_client.assert_awaited_once_with(registration)


@pytest.mark.asyncio
async def test_should_stop_and_raise_on_inappropriate_content() -> None:
    # Arrange
    service, openai, vectors, storage = _service(insult=True)

    # Act / Assert
    with pytest.raises(InappropriateContentError):
        await service.register(_registration())

    openai.generate_embeddings_from_chunks.assert_not_awaited()
    vectors.upsert_company_vectors.assert_not_awaited()
    storage.save_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_moderate_content_built_from_company_fields() -> None:
    # Arrange
    service, openai, _, _ = _service()

    # Act
    await service.register(_registration(name="Padaria"))

    # Assert
    content = openai.moderate.await_args.args[0]
    assert "Padaria" in content
    assert "bolos e paes" in content
    assert "rua a, 10" in content


@pytest.mark.asyncio
async def test_should_upsert_the_generated_embeddings() -> None:
    # Arrange
    records = [EmbeddingRecord(text="c1", vector=[0.1])]
    service, _, vectors, _ = _service(embeddings=records)

    # Act
    await service.register(_registration())

    # Assert
    assert vectors.upsert_company_vectors.await_args.args[2] == records


@pytest.mark.asyncio
async def test_should_replace_vectors_when_same_user_code_registers_again() -> None:
    # Arrange
    service, _, vectors, _ = _service()

    # Act
    await service.register(_registration("123", "Nome Antigo"))
    await service.register(_registration("123", "Nome Novo"))

    # Assert
    assert vectors.upsert_company_vectors.await_count == 2
    assert all(
        call.args[1] == "123"
        for call in vectors.upsert_company_vectors.await_args_list
    )
