"""Integration tests: domain models wired into FastAPI with ``ApiResponse``.

Mount the boundary schemas on a minimal FastAPI app and exercise them through
the HTTP stack to confirm validation (valid accepted, invalid rejected with
422) and that the shared :class:`ApiResponse` envelope serializes correctly.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.schemas import (
    ApiResponse,
    CompanyRegistrationRequest,
    OnlineChatSearchPayload,
    WhatsAppSearchPayload,
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.post("/companies", response_model=ApiResponse)
    async def register_company(payload: CompanyRegistrationRequest) -> ApiResponse:
        return ApiResponse(status_code=201, message=f"registered {payload.user_code}")

    @app.post("/whatsapp", response_model=ApiResponse)
    async def whatsapp(payload: WhatsAppSearchPayload) -> ApiResponse:
        return ApiResponse(status_code=200, message=payload.text)

    @app.post("/online", response_model=ApiResponse)
    async def online(payload: OnlineChatSearchPayload) -> ApiResponse:
        return ApiResponse(status_code=200, message=payload.message)

    return TestClient(app)


def test_should_accept_valid_company_registration(client: TestClient) -> None:
    # Arrange
    payload = {
        "user_code": "1234567890",
        "request": {
            "name": "nome da empresa",
            "descricao": "descricao da empresa",
            "email": "contato@empresa.com.br",
            "address": "endereco",
            "telephone": "5535999999999",
            "detalhes": "Seg a Sex 08h-19h",
        },
    }

    # Act
    response = client.post("/companies", json=payload)

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status_code": 201,
        "message": "registered 1234567890",
        "errors": [],
    }


def test_should_reject_company_with_invalid_email(client: TestClient) -> None:
    # Arrange
    payload = {
        "user_code": "1234567890",
        "request": {
            "name": "nome",
            "descricao": "descricao",
            "email": "invalid",
            "address": "endereco",
            "telephone": "123",
            "detalhes": "detalhes",
        },
    }

    # Act
    response = client.post("/companies", json=payload)

    # Assert
    assert response.status_code == 422


def test_should_accept_whatsapp_payload_with_camel_case_alias(
    client: TestClient,
) -> None:
    # Arrange
    payload = {"number": "5535999999999", "text": "ola", "linkPreview": True}

    # Act
    response = client.post("/whatsapp", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "ola"


def test_should_accept_valid_online_chat_payload(client: TestClient) -> None:
    # Arrange
    payload = {
        "message": "onde posso comer?",
        "user_code": "4567895465",
        "user_ip": "200.148.12.188",
    }

    # Act
    response = client.post("/online", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "onde posso comer?"


def test_should_reject_online_chat_with_invalid_ip(client: TestClient) -> None:
    # Arrange
    payload = {
        "message": "ola",
        "user_code": "4567895465",
        "user_ip": "not-an-ip",
    }

    # Act
    response = client.post("/online", json=payload)

    # Assert
    assert response.status_code == 422
