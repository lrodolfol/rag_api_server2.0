"""Unit tests for :class:`RegistrationService` with mocked dependencies."""

import logging
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.registration import RegistrationService
from app.domain import (
    Category,
    CompanyRegistrationRequest,
    EmbeddingRecord,
    InappropriateContentError,
)
from app.infrastructure.openai import ModerationResult

CATALOG = ["ALIMENTAÇÃO", "BELEZA"]


@dataclass
class Mocks:
    service: RegistrationService
    openai: AsyncMock
    vectors: AsyncMock
    storage: AsyncMock
    categories: AsyncMock


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


def _mocks(
    *,
    insult: bool = False,
    llm_category: str = "ALIMENTAÇÃO",
    resolved: str = "ALIMENTAÇÃO",
    previous_slug: str | None = None,
    embeddings: list[EmbeddingRecord] | None = None,
) -> Mocks:
    openai = AsyncMock()
    openai.moderate.return_value = ModerationResult(
        insult=insult, insult_text="", category=llm_category
    )
    openai.generate_embeddings_from_chunks.return_value = (
        embeddings if embeddings is not None else [EmbeddingRecord(text="bolos", vector=[0.1])]
    )
    vectors = AsyncMock()
    vectors.get_category_by_user_code.return_value = previous_slug
    storage = AsyncMock()
    categories = AsyncMock()
    categories.list_names.return_value = list(CATALOG)
    categories.resolve_or_create.return_value = Category.from_name(resolved)
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
        category_service=categories,
    )
    return Mocks(service, openai, vectors, storage, categories)


@pytest.mark.asyncio
async def test_should_store_vectors_and_record_in_category_on_first_registration() -> None:
    # Arrange
    mocks = _mocks(previous_slug=None)
    registration = _registration("123", "Padaria")

    # Act
    await mocks.service.register(registration)

    # Assert
    mocks.openai.moderate.assert_awaited_once()
    assert mocks.openai.moderate.await_args.args[1] == CATALOG
    mocks.categories.resolve_or_create.assert_awaited_once_with("ALIMENTAÇÃO")
    upsert_args = mocks.vectors.upsert_company_vectors.await_args.args
    assert upsert_args[:3] == ("Padaria", "123", "alimentacao")
    mocks.storage.delete_client.assert_not_awaited()
    mocks.storage.save_client.assert_awaited_once_with(registration, "alimentacao")


@pytest.mark.asyncio
async def test_should_move_record_when_category_changes() -> None:
    # Arrange
    mocks = _mocks(llm_category="BELEZA", resolved="BELEZA", previous_slug="alimentacao")
    registration = _registration("123", "Salao")

    # Act
    await mocks.service.register(registration)

    # Assert
    assert mocks.vectors.upsert_company_vectors.await_args.args[2] == "beleza"
    mocks.storage.delete_client.assert_awaited_once_with("123", "alimentacao")
    mocks.storage.save_client.assert_awaited_once_with(registration, "beleza")


@pytest.mark.asyncio
async def test_should_not_remove_anything_when_category_is_the_same() -> None:
    # Arrange
    mocks = _mocks(previous_slug="alimentacao")

    # Act
    await mocks.service.register(_registration())

    # Assert
    mocks.storage.delete_client.assert_not_awaited()
    mocks.storage.save_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_should_stop_without_any_write_on_inappropriate_content() -> None:
    # Arrange
    mocks = _mocks(insult=True)

    # Act / Assert
    with pytest.raises(InappropriateContentError):
        await mocks.service.register(_registration())

    mocks.categories.resolve_or_create.assert_not_awaited()
    mocks.vectors.get_category_by_user_code.assert_not_awaited()
    mocks.openai.generate_embeddings_from_chunks.assert_not_awaited()
    mocks.vectors.upsert_company_vectors.assert_not_awaited()
    mocks.storage.delete_client.assert_not_awaited()
    mocks.storage.save_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_read_previous_category_before_upsert_and_write_in_order() -> None:
    # Arrange
    mocks = _mocks(llm_category="BELEZA", resolved="BELEZA", previous_slug="alimentacao")
    calls = MagicMock()
    calls.attach_mock(mocks.vectors.get_category_by_user_code, "read_previous")
    calls.attach_mock(mocks.vectors.upsert_company_vectors, "upsert")
    calls.attach_mock(mocks.storage.delete_client, "delete_old")
    calls.attach_mock(mocks.storage.save_client, "save_new")

    # Act
    await mocks.service.register(_registration())

    # Assert
    assert [call[0] for call in calls.mock_calls] == [
        "read_previous",
        "upsert",
        "delete_old",
        "save_new",
    ]


@pytest.mark.asyncio
async def test_should_moderate_content_built_from_company_fields() -> None:
    # Arrange
    mocks = _mocks()

    # Act
    await mocks.service.register(_registration(name="Padaria"))

    # Assert
    content = mocks.openai.moderate.await_args.args[0]
    assert "Padaria" in content
    assert "bolos e paes" in content
    assert "rua a, 10" in content


@pytest.mark.asyncio
async def test_should_upsert_the_generated_embeddings() -> None:
    # Arrange
    records = [EmbeddingRecord(text="c1", vector=[0.1])]
    mocks = _mocks(embeddings=records)

    # Act
    await mocks.service.register(_registration())

    # Assert
    assert mocks.vectors.upsert_company_vectors.await_args.args[3] == records


@pytest.mark.asyncio
async def test_should_log_category_but_never_user_code_or_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    mocks = _mocks(llm_category="BELEZA", resolved="BELEZA", previous_slug="alimentacao")

    # Act
    with caplog.at_level(logging.INFO):
        await mocks.service.register(_registration("secret-code", "Salao Secreto"))

    # Assert
    assert "Registration category defined: 'BELEZA'" in caplog.text
    assert "changed from 'alimentacao' to 'beleza'" in caplog.text
    assert "secret-code" not in caplog.text
    assert "Salao Secreto" not in caplog.text
