"""Unit tests for :class:`DeletionService` with mocked repositories."""

import logging
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.deletion import DeletionService
from app.domain import (
    ClientStorageError,
    CompanyDeletionRequest,
    VectorRepositoryError,
)


@dataclass
class Mocks:
    service: DeletionService
    vectors: AsyncMock
    storage: AsyncMock
    semantic_cache: AsyncMock
    answer_cache: AsyncMock


def _mocks(*, has_vectors: bool = True, category: str | None = "beleza") -> Mocks:
    vectors = AsyncMock()
    vectors.has_vectors_for_user_code.return_value = has_vectors
    vectors.get_category_by_user_code.return_value = category
    storage = AsyncMock()
    semantic_cache = AsyncMock()
    answer_cache = AsyncMock()
    service = DeletionService(
        vector_repository=vectors,
        storage_repository=storage,
        semantic_cache=semantic_cache,
        answer_cache=answer_cache,
    )
    return Mocks(service, vectors, storage, semantic_cache, answer_cache)


@pytest.mark.asyncio
async def test_should_read_category_then_delete_vectors_then_category_record() -> None:
    # Arrange
    mocks = _mocks(has_vectors=True, category="beleza")
    calls = MagicMock()
    calls.attach_mock(mocks.vectors.get_category_by_user_code, "read_category")
    calls.attach_mock(mocks.vectors.delete_by_user_code, "delete_vectors")
    calls.attach_mock(mocks.semantic_cache.invalidate_category, "invalidate_semantic")
    calls.attach_mock(mocks.answer_cache.invalidate_category, "invalidate_exact")
    calls.attach_mock(mocks.storage.delete_client, "delete_client")

    # Act
    await mocks.service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    mocks.vectors.has_vectors_for_user_code.assert_awaited_once_with("123")
    assert [call[0] for call in calls.mock_calls] == [
        "read_category",
        "delete_vectors",
        "invalidate_semantic",
        "invalidate_exact",
        "delete_client",
    ]
    mocks.semantic_cache.invalidate_category.assert_awaited_once_with("beleza")
    mocks.answer_cache.invalidate_category.assert_awaited_once_with("beleza")
    mocks.vectors.get_category_by_user_code.assert_awaited_once_with("123")
    mocks.vectors.delete_by_user_code.assert_awaited_once_with("123")
    mocks.storage.delete_client.assert_awaited_once_with("123", "beleza")


@pytest.mark.asyncio
async def test_should_do_nothing_when_no_vectors_exist() -> None:
    # Arrange
    mocks = _mocks(has_vectors=False)

    # Act
    await mocks.service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    mocks.vectors.get_category_by_user_code.assert_not_awaited()
    mocks.vectors.delete_by_user_code.assert_not_awaited()
    mocks.storage.delete_client.assert_not_awaited()
    mocks.semantic_cache.invalidate_category.assert_not_awaited()
    mocks.answer_cache.invalidate_category.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_delete_only_vectors_and_warn_for_legacy_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Arrange
    mocks = _mocks(has_vectors=True, category=None)

    # Act
    with caplog.at_level(logging.WARNING):
        await mocks.service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    mocks.vectors.delete_by_user_code.assert_awaited_once_with("123")
    mocks.semantic_cache.invalidate_category.assert_awaited_once_with(None)
    mocks.answer_cache.invalidate_category.assert_awaited_once_with(None)
    mocks.storage.delete_client.assert_not_awaited()
    assert "legacy record was not removed from the bucket" in caplog.text


@pytest.mark.asyncio
async def test_should_propagate_vector_error_and_skip_storage() -> None:
    # Arrange
    mocks = _mocks(has_vectors=True)
    mocks.vectors.delete_by_user_code.side_effect = VectorRepositoryError("boom")

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await mocks.service.delete(CompanyDeletionRequest(user_code="123"))
    mocks.semantic_cache.invalidate_category.assert_not_awaited()
    mocks.answer_cache.invalidate_category.assert_not_awaited()
    mocks.storage.delete_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_propagate_category_read_error_and_delete_nothing() -> None:
    # Arrange
    mocks = _mocks(has_vectors=True)
    mocks.vectors.get_category_by_user_code.side_effect = VectorRepositoryError("boom")

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await mocks.service.delete(CompanyDeletionRequest(user_code="123"))
    mocks.vectors.delete_by_user_code.assert_not_awaited()
    mocks.storage.delete_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_propagate_storage_error() -> None:
    # Arrange
    mocks = _mocks(has_vectors=True)
    mocks.storage.delete_client.side_effect = ClientStorageError("boom")

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await mocks.service.delete(CompanyDeletionRequest(user_code="123"))


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ["beleza", None])
async def test_should_not_log_user_code(
    caplog: pytest.LogCaptureFixture, category: str | None
) -> None:
    # Arrange
    mocks = _mocks(has_vectors=True, category=category)

    # Act
    with caplog.at_level("INFO"):
        await mocks.service.delete(CompanyDeletionRequest(user_code="secret-code"))

    # Assert
    assert "secret-code" not in caplog.text
