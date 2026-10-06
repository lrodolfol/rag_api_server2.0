"""Unit tests for the conversation domain models."""

import pytest
from pydantic import ValidationError

from app.domain import MessageHistoryItem, MessageRole, PayloadQuestionOpenIA


def test_should_flag_user_message() -> None:
    # Arrange / Act
    item = MessageHistoryItem(role=MessageRole.USER, text="ola")

    # Assert
    assert item.is_user is True


def test_should_flag_assistant_message() -> None:
    # Arrange / Act
    item = MessageHistoryItem(role=MessageRole.ASSISTANT, text="oi, tudo bem?")

    # Assert
    assert item.is_user is False


def test_should_reject_unknown_role() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        MessageHistoryItem.model_validate({"role": "system", "text": "x"})


def test_should_default_chat_historic_to_empty_list() -> None:
    # Arrange / Act
    payload = PayloadQuestionOpenIA(question="onde posso comer?")

    # Assert
    assert payload.chat_historic == []
    assert payload.is_invalid() is False


def test_should_consider_blank_question_invalid() -> None:
    # Arrange / Act
    payload = PayloadQuestionOpenIA(question="   ")

    # Assert
    assert payload.is_invalid() is True


def test_should_build_payload_with_history() -> None:
    # Arrange
    data = {
        "question": "e sobremesa?",
        "chat_historic": [
            {"role": "user", "text": "onde posso comer?"},
            {"role": "assistant", "text": "ha varias opcoes perto de voce."},
        ],
    }

    # Act
    payload = PayloadQuestionOpenIA.model_validate(data)

    # Assert
    assert len(payload.chat_historic) == 2
    assert payload.chat_historic[0].is_user is True
    assert payload.chat_historic[1].is_user is False
