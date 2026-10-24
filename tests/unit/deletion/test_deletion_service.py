"""Unit tests for :class:`DeletionService` with mocked repositories."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.deletion import DeletionService
from app.domain import (
    ClientStorageError,
    CompanyDeletionRequest,
    VectorRepositoryError,
)

Mocks = tuple[DeletionService, AsyncMock, AsyncMock]


def _service(*, has_vectors: bool = True) -> Mocks:
    vectors = AsyncMock()
    vectors.has_vectors_for_user_code.return_value = has_vectors
    storage = AsyncMock()
    service = DeletionService(vector_repository=vectors, storage_repository=storage)
    return service, vectors, storage


@pytest.mark.asyncio
async def test_should_delete_vectors_then_storage_record_when_vectors_exist() -> None:
    # Arrange
    service, vectors, storage = _service(has_vectors=True)
    calls = MagicMock()
    calls.attach_mock(vectors.delete_by_user_code, "delete_vectors")
    calls.attach_mock(storage.delete_client, "delete_client")

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    vectors.has_vectors_for_user_code.assert_awaited_once_with("123")
    assert [call[0] for call in calls.mock_calls] == ["delete_vectors", "delete_client"]
    vectors.delete_by_user_code.assert_awaited_once_with("123")
    storage.delete_client.assert_awaited_once_with("123")


@pytest.mark.asyncio
async def test_should_do_nothing_when_no_vectors_exist() -> None:
    # Arrange
    service, vectors, storage = _service(has_vectors=False)

    # Act
    await service.delete(CompanyDeletionRequest(user_code="123"))

    # Assert
    vectors.delete_by_user_code.assert_not_awaited()
    storage.delete_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_propagate_vector_error_and_skip_storage() -> None:
    # Arrange
    service, vectors, storage = _service(has_vectors=True)
    vectors.delete_by_user_code.side_effect = VectorRepositoryError("boom")

    # Act / Assert
    with pytest.raises(VectorRepositoryError):
        await service.delete(CompanyDeletionRequest(user_code="123"))
    storage.delete_client.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_propagate_storage_error() -> None:
    # Arrange
    service, _, storage = _service(has_vectors=True)
    storage.delete_client.side_effect = ClientStorageError("boom")

    # Act / Assert
    with pytest.raises(ClientStorageError):
        await service.delete(CompanyDeletionRequest(user_code="123"))


@pytest.mark.asyncio
async def test_should_not_log_user_code(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    service, _, _ = _service(has_vectors=True)

    # Act
    with caplog.at_level("INFO"):
        await service.delete(CompanyDeletionRequest(user_code="secret-code"))

    # Assert
    assert "secret-code" not in caplog.text
