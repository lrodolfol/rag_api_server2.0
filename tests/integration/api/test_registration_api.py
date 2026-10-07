"""Integration tests for the company registration endpoint.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the
registration service is replaced with a fake via dependency override so no
external provider is contacted.
"""

from fastapi.testclient import TestClient

from app.api.dependencies import get_registration_service
from app.domain import CompanyRegistrationRequest, InappropriateContentError
from app.main import create_app


class _FakeRegistrationService:
    """In-memory stand-in recording registrations and optionally rejecting them."""

    def __init__(self, *, insult: bool = False) -> None:
        self._insult = insult
        self.calls: list[CompanyRegistrationRequest] = []

    async def register(self, registration: CompanyRegistrationRequest) -> None:
        self.calls.append(registration)
        if self._insult:
            raise InappropriateContentError(
                "Submitted content was rejected by moderation"
            )


def _payload(user_code: str = "123", name: str = "Padaria") -> dict:
    return {
        "user_code": user_code,
        "request": {
            "name": name,
            "descricao": "bolos",
            "email": "shop@example.com",
            "address": "rua a",
            "telephone": "1199999",
            "detalhes": "detalhes",
        },
    }


def _client(service: _FakeRegistrationService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    return TestClient(app)


def test_should_register_company_and_return_created_envelope() -> None:
    # Arrange
    service = _FakeRegistrationService()
    client = _client(service)

    # Act
    response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    body = response.json()
    assert body["status_code"] == 201
    assert body["errors"] == []
    assert len(service.calls) == 1
    assert service.calls[0].user_code == "123"


def test_should_reject_inappropriate_content_without_persisting() -> None:
    # Arrange
    service = _FakeRegistrationService(insult=True)
    client = _client(service)

    # Act
    response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert body["status_code"] == 400
    assert "inappropriate_content" in body["errors"]


def test_should_reject_invalid_payload_with_validation_error() -> None:
    # Arrange
    service = _FakeRegistrationService()
    client = _client(service)

    # Act
    response = client.post("/companies", json={"user_code": "123"})

    # Assert
    assert response.status_code == 422
    assert service.calls == []
