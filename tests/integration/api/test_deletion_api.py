"""Integration tests for the company deletion endpoint.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the
deletion service is replaced with a fake via dependency override so no external
provider is contacted.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.api.dependencies import get_deletion_service
from app.domain import (
    ClientStorageError,
    CompanyDeletionRequest,
    DomainError,
    VectorRepositoryError,
)
from app.main import create_app


class _FakeDeletionService:
    """In-memory stand-in recording deletions and optionally failing them."""

    def __init__(self, *, error: DomainError | None = None) -> None:
        self._error = error
        self.calls: list[CompanyDeletionRequest] = []

    async def delete(self, request: CompanyDeletionRequest) -> None:
        self.calls.append(request)
        if self._error:
            raise self._error


def _delete(service: _FakeDeletionService, payload: dict | None) -> Response:
    app = create_app()
    app.dependency_overrides[get_deletion_service] = lambda: service
    client = TestClient(app, raise_server_exceptions=False)
    return client.request("DELETE", "/companies", json=payload)


def test_should_delete_company_and_return_ok_envelope() -> None:
    # Arrange
    service = _FakeDeletionService()

    # Act
    response = _delete(service, {"user_code": "rodolfo12301"})

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == 200
    assert body["errors"] == []
    assert [call.user_code for call in service.calls] == ["rodolfo12301"]


@pytest.mark.parametrize("payload", [None, {}, {"user_code": ""}])
def test_should_reject_invalid_payload_with_validation_error(payload: dict | None) -> None:
    # Arrange
    service = _FakeDeletionService()

    # Act
    response = _delete(service, payload)

    # Assert
    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.parametrize(
    "error",
    [
        VectorRepositoryError("Failed to delete vectors"),
        ClientStorageError("Failed to persist client record"),
    ],
)
def test_should_return_safe_internal_error_envelope(error: DomainError) -> None:
    # Arrange
    service = _FakeDeletionService(error=error)

    # Act
    response = _delete(service, {"user_code": "123"})

    # Assert
    assert response.status_code == 500
    body = response.json()
    assert body["status_code"] == 500
    assert body["errors"] == ["internal_error"]
    assert str(error) not in body["message"]
