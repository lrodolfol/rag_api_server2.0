"""Unit tests for API schemas and domain entities."""

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    BusinessCreateRequest,
    SearchResponse,
    SearchResult,
    UserMessageRequest,
)
from app.domain.message import ConversationHistory, Message, MessageRole


def _valid_business() -> dict:
    return {
        "name": "Padaria Central",
        "description": "Pães e café",
        "email": "contato@padaria.com",
        "phone": "11999999999",
    }


def test_should_accept_valid_business_request() -> None:
    result = BusinessCreateRequest(**_valid_business())

    assert result.has_delivery is False
    assert result.whatsapp is None


def test_should_reject_business_without_required_fields() -> None:
    with pytest.raises(ValidationError):
        BusinessCreateRequest(name="Sem dados")


def test_should_reject_invalid_email() -> None:
    data = _valid_business() | {"email": "not-an-email"}

    with pytest.raises(ValidationError):
        BusinessCreateRequest(**data)


def test_should_reject_empty_user_message() -> None:
    with pytest.raises(ValidationError):
        UserMessageRequest(user_id="u1", message="")


def test_should_reject_too_long_user_message() -> None:
    with pytest.raises(ValidationError):
        UserMessageRequest(user_id="u1", message="a" * 1001)


def test_should_limit_search_response_to_five_results() -> None:
    results = [SearchResult(name=f"n{i}", description="d") for i in range(6)]

    with pytest.raises(ValidationError):
        SearchResponse(results=results)


def test_should_append_message_to_conversation_history() -> None:
    history = ConversationHistory(user_id="u1")

    history.add(Message(role=MessageRole.USER, content="onde comer?"))

    assert history.messages[0].content == "onde comer?"
