"""Unit tests for the ChatAnswer domain model."""

import pytest

from app.domain import ChatAnswer, DomainError, InvalidChatAnswerError


def test_should_parse_items_from_valid_json() -> None:
    # Act
    answer = ChatAnswer.from_json('{"respostas": ["a", "b"]}')

    # Assert
    assert answer.respostas == ["a", "b"]


def test_should_parse_empty_array_as_empty_answer() -> None:
    # Act
    answer = ChatAnswer.from_json('{"respostas": []}')

    # Assert
    assert answer.is_empty() is True


def test_should_drop_blank_items_and_strip_spaces() -> None:
    # Act
    answer = ChatAnswer.from_json('{"respostas": ["  a  ", "", "   ", "\\n", "b"]}')

    # Assert
    assert answer.respostas == ["a", "b"]


def test_should_be_empty_when_every_item_is_blank() -> None:
    # Act
    answer = ChatAnswer(respostas=["", "  "])

    # Assert
    assert answer.is_empty() is True


def test_should_default_to_empty_items() -> None:
    # Act / Assert
    assert ChatAnswer().respostas == []


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "",
        '{"respostas": ["a"',
        "{}",
        '{"answers": ["a"]}',
        '["a", "b"]',
        '"texto"',
        '{"respostas": "a"}',
        '{"respostas": [1, 2]}',
        '{"respostas": null}',
    ],
)
def test_should_raise_domain_error_for_invalid_json(raw: str) -> None:
    # Act / Assert
    with pytest.raises(InvalidChatAnswerError):
        ChatAnswer.from_json(raw)


def test_invalid_answer_error_should_be_a_domain_error() -> None:
    # Act / Assert
    assert issubclass(InvalidChatAnswerError, DomainError)


def test_should_serialize_to_expected_json_keeping_accents() -> None:
    # Arrange
    answer = ChatAnswer(respostas=["Padaria São João", "Café"])

    # Act
    raw = answer.to_json()

    # Assert
    assert raw == '{"respostas": ["Padaria São João", "Café"]}'


def test_should_round_trip_through_json() -> None:
    # Arrange
    original = ChatAnswer(respostas=["a", "b"])

    # Act
    restored = ChatAnswer.from_json(original.to_json())

    # Assert
    assert restored == original


def test_should_merge_keeping_order_and_removing_duplicates() -> None:
    # Arrange
    first = ChatAnswer(respostas=["a", "b"])
    second = ChatAnswer(respostas=["b", "c", "a", "d"])

    # Act
    merged = ChatAnswer.merge([first, second])

    # Assert
    assert merged.respostas == ["a", "b", "c", "d"]


def test_should_merge_ignoring_empty_answers() -> None:
    # Arrange
    answers = [ChatAnswer(), ChatAnswer(respostas=["a"]), ChatAnswer()]

    # Act
    merged = ChatAnswer.merge(answers)

    # Assert
    assert merged.respostas == ["a"]


def test_should_merge_empty_list_into_empty_answer() -> None:
    # Act / Assert
    assert ChatAnswer.merge([]).is_empty() is True


def test_should_join_items_with_blank_line_by_default() -> None:
    # Arrange
    answer = ChatAnswer(respostas=["a", "b"])

    # Act / Assert
    assert answer.as_text() == "a\n\nb"


def test_should_join_items_with_custom_separator() -> None:
    # Arrange
    answer = ChatAnswer(respostas=["a", "b"])

    # Act / Assert
    assert answer.as_text(" | ") == "a | b"


def test_should_return_empty_text_for_empty_answer() -> None:
    # Act / Assert
    assert ChatAnswer().as_text() == ""
