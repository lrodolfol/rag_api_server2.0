"""Unit tests for the search payload domain models."""

import pytest
from pydantic import ValidationError

from app.domain import OnlineChatSearchPayload, WhatsAppSearchPayload


def test_should_accept_valid_whatsapp_payload_with_alias() -> None:
    # Arrange
    payload = {
        "number": "5535999999999",
        "text": "Ola! mensagem de teste.",
        "delay": 1200,
        "linkPreview": False,
    }

    # Act
    model = WhatsAppSearchPayload.model_validate(payload)

    # Assert
    assert model.number == "5535999999999"
    assert model.delay == 1200
    assert model.link_preview is False


def test_should_default_whatsapp_optional_fields() -> None:
    # Arrange
    payload = {"number": "5535999999999", "text": "ola"}

    # Act
    model = WhatsAppSearchPayload.model_validate(payload)

    # Assert
    assert model.delay is None
    assert model.link_preview is False


def test_should_serialize_whatsapp_link_preview_by_alias() -> None:
    # Arrange
    model = WhatsAppSearchPayload(number="5535999999999", text="ola")

    # Act
    dumped = model.model_dump(by_alias=True)

    # Assert
    assert "linkPreview" in dumped


def test_should_reject_whatsapp_without_text() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        WhatsAppSearchPayload.model_validate({"number": "5535999999999"})


def test_should_accept_valid_online_chat_payload() -> None:
    # Arrange
    payload = {
        "message": "onde posso comer?",
        "user_code": "4567895465",
        "user_ip": "200.148.12.188",
    }

    # Act
    model = OnlineChatSearchPayload.model_validate(payload)

    # Assert
    assert model.message == "onde posso comer?"
    assert str(model.user_ip) == "200.148.12.188"


def test_should_reject_online_chat_with_invalid_ip() -> None:
    # Arrange
    payload = {
        "message": "ola",
        "user_code": "4567895465",
        "user_ip": "not-an-ip",
    }

    # Act / Assert
    with pytest.raises(ValidationError):
        OnlineChatSearchPayload.model_validate(payload)


def test_should_reject_online_chat_with_empty_message() -> None:
    # Arrange
    payload = {"message": "", "user_code": "4567895465", "user_ip": "200.148.12.188"}

    # Act / Assert
    with pytest.raises(ValidationError):
        OnlineChatSearchPayload.model_validate(payload)
