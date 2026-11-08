"""Unit tests for the answer caching policy with ``ChatAnswer``."""

import pytest

from app.application.cache import is_cacheable_answer
from app.domain import ChatAnswer


def test_should_not_cache_empty_chat_answer() -> None:
    # Act / Assert
    assert is_cacheable_answer(ChatAnswer(respostas=[])) is False


def test_should_not_cache_chat_answer_with_only_blank_items() -> None:
    # Act / Assert
    assert is_cacheable_answer(ChatAnswer(respostas=["", "  "])) is False


@pytest.mark.parametrize("items", [["Padaria Central"], ["a", "b"]])
def test_should_cache_filled_chat_answer(items: list[str]) -> None:
    # Act / Assert
    assert is_cacheable_answer(ChatAnswer(respostas=items)) is True
