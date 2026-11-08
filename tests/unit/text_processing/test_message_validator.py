"""Unit tests for the short-message detector (no LLM involved)."""

import pytest

from app.application.text_processing import MIN_MESSAGE_LETTERS, is_short_message


@pytest.mark.parametrize(
    "message",
    ["...", "i", "!!", "1234", " ", "   ", "", "a1", "é?", "😀😀", "\n\t", "1 2 3 !"],
)
def test_should_identify_short_message(message: str) -> None:
    # Act
    result = is_short_message(message)

    # Assert
    assert result is True


@pytest.mark.parametrize(
    "message",
    ["oi", "ok", "  oi  ", "pizzaria no centro", "onde tem açaí?", "çã", "rua 15"],
)
def test_should_not_identify_valid_message_as_short(message: str) -> None:
    # Act
    result = is_short_message(message)

    # Assert
    assert result is False


def test_should_require_two_letters_as_minimum() -> None:
    # Assert
    assert MIN_MESSAGE_LETTERS == 2
