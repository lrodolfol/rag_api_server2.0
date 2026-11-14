"""Unit tests for the answer-cache domain models."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain import CacheFingerprint, SemanticCacheEntry, SemanticCacheMatch

FINGERPRINT = CacheFingerprint(
    prompt_version="1.0.0",
    rules_version="1.0.0",
    model_capability="economic",
    normalized_text="onde vende marmitas?",
)


def _entry(**overrides: object) -> SemanticCacheEntry:
    fields: dict[str, object] = {
        "id": uuid4(),
        "fingerprint": FINGERPRINT,
        "input_text": "Onde vende marmitas?",
        "response": "Marmitaria Central",
        "embedding": [0.1, 0.2],
        "created_at": datetime(2026, 11, 10, 12, 0, 0),
    }
    fields.update(overrides)
    return SemanticCacheEntry.model_validate(fields)


def test_should_default_category_to_none() -> None:
    # Act
    entry = _entry()

    # Assert
    assert entry.category is None


def test_should_keep_category_slug() -> None:
    # Act
    entry = _entry(category="alimentacao")

    # Assert
    assert entry.category == "alimentacao"


def test_should_stay_immutable() -> None:
    # Arrange
    entry = _entry(category="alimentacao")

    # Act / Assert
    with pytest.raises(ValidationError):
        entry.category = "beleza"  # type: ignore[misc]


def test_should_reject_blank_category() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        _entry(category="")


def _match(**overrides: object) -> SemanticCacheMatch:
    fields: dict[str, object] = {
        "input_text": "Onde vende marmitas?",
        "response": "Marmitaria Central",
        "distance": 0.1,
        "similarity": 0.9,
    }
    fields.update(overrides)
    return SemanticCacheMatch.model_validate(fields)


def test_should_default_match_category_to_none() -> None:
    # Act
    match = _match()

    # Assert
    assert match.category is None


def test_should_keep_match_category_slug() -> None:
    # Act
    match = _match(category="alimentacao")

    # Assert
    assert match.category == "alimentacao"


def test_should_reject_blank_match_category() -> None:
    # Act / Assert
    with pytest.raises(ValidationError):
        _match(category="")
