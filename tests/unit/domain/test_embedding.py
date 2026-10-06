"""Unit tests for the embedding domain model."""

import pytest
from pydantic import ValidationError

from app.domain import EmbeddingRecord


def test_should_accept_valid_embedding_record() -> None:
    # Arrange / Act
    record = EmbeddingRecord(text="chunk de texto", vector=[0.1, 0.2, 0.3])

    # Assert
    assert record.text == "chunk de texto"
    assert record.vector == [0.1, 0.2, 0.3]


def test_should_reject_empty_text() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        EmbeddingRecord(text="", vector=[0.1])


def test_should_reject_non_numeric_vector() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        EmbeddingRecord.model_validate({"text": "x", "vector": ["a", "b"]})
