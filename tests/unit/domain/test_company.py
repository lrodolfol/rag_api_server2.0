"""Unit tests for the company registration domain models."""

import pytest
from pydantic import ValidationError

from app.domain import CompanyData, CompanyRegistrationRequest


def _valid_company_payload() -> dict:
    return {
        "name": "nome da empresa",
        "descricao": "descricao da empresa",
        "email": "contato@empresa.com.br",
        "address": "endereco da empresa",
        "telephone": "5535999999999",
        "detalhes": "Horario: Seg a Sex 08h-19h",
    }


def test_should_accept_a_valid_registration_request() -> None:
    # Arrange
    payload = {"user_code": "1234567890", "request": _valid_company_payload()}

    # Act
    request = CompanyRegistrationRequest.model_validate(payload)

    # Assert
    assert request.user_code == "1234567890"
    assert isinstance(request.request, CompanyData)
    assert request.request.email == "contato@empresa.com.br"


def test_should_reject_invalid_email() -> None:
    # Arrange
    data = _valid_company_payload()
    data["email"] = "not-an-email"

    # Act / Assert
    with pytest.raises(ValidationError):
        CompanyData.model_validate(data)


def test_should_reject_empty_name() -> None:
    # Arrange
    data = _valid_company_payload()
    data["name"] = ""

    # Act / Assert
    with pytest.raises(ValidationError):
        CompanyData.model_validate(data)


def test_should_reject_request_without_user_code() -> None:
    # Arrange
    payload = {"request": _valid_company_payload()}

    # Act / Assert
    with pytest.raises(ValidationError):
        CompanyRegistrationRequest.model_validate(payload)


def test_should_reject_empty_user_code() -> None:
    # Arrange
    payload = {"user_code": "", "request": _valid_company_payload()}

    # Act / Assert
    with pytest.raises(ValidationError):
        CompanyRegistrationRequest.model_validate(payload)
