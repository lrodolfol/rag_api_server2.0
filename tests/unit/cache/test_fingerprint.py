"""Unit tests for the answer-cache fingerprint and key generation."""

import re

import pytest

from app.application.cache import (
    build_cache_key,
    build_fingerprint,
    normalize_question_finger_print,
)
from app.infrastructure.config import FingerPrintConfig

SHA256_HEX_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def config() -> FingerPrintConfig:
    return FingerPrintConfig(
        prompt_version="1.0.0", rules_version="1.0.0", model_capability="economic"
    )


def _key(question: str, config: FingerPrintConfig) -> str:
    return build_cache_key(build_fingerprint(question, config))


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("  onde posso comer?  ", "onde posso comer?"),
        ("Onde Posso COMER?", "onde posso comer?"),
        ("onde   posso\n\tcomer?", "onde posso comer?"),
        ("Pizzaria com promoção à noite", "pizzaria com promocao a noite"),
        ("AÇAÍ perto de mim", "acai perto de mim"),
    ],
)
def test_should_normalize_question(question: str, expected: str) -> None:
    # Act
    result = normalize_question_finger_print(question)

    # Assert
    assert result == expected


def test_should_build_fingerprint_from_config_and_normalized_question(
    config: FingerPrintConfig,
) -> None:
    # Act
    fingerprint = build_fingerprint("  Onde posso COMER?\n", config)

    # Assert
    assert fingerprint.prompt_version == "1.0.0"
    assert fingerprint.rules_version == "1.0.0"
    assert fingerprint.model_capability == "economic"
    assert fingerprint.normalized_text == "onde posso comer?"


def test_should_build_deterministic_sha256_key(config: FingerPrintConfig) -> None:
    # Act
    first_key = _key("onde posso comer?", config)
    second_key = _key("onde posso comer?", config)

    # Assert
    assert first_key == second_key
    assert SHA256_HEX_PATTERN.match(first_key)


def test_should_build_same_key_for_equivalent_questions(
    config: FingerPrintConfig,
) -> None:
    # Act / Assert
    assert _key("  Onde posso COMER?\n", config) == _key("onde posso comer?", config)
    assert _key("Açaí perto", config) == _key("acai perto", config)


def test_should_build_different_keys_for_different_questions(
    config: FingerPrintConfig,
) -> None:
    # Act / Assert
    assert _key("onde posso comer?", config) != _key("onde posso dormir?", config)


@pytest.mark.parametrize(
    ("field", "new_value"),
    [
        ("prompt_version", "1.0.1"),
        ("rules_version", "2.0.0"),
        ("model_capability", "stronger"),
    ],
)
def test_should_change_key_when_any_version_changes(
    config: FingerPrintConfig, field: str, new_value: str
) -> None:
    # Arrange
    changed_config = config.model_copy(update={field: new_value})

    # Act / Assert
    assert _key("onde posso comer?", config) != _key("onde posso comer?", changed_config)


def test_should_not_allow_fingerprint_mutation(config: FingerPrintConfig) -> None:
    # Arrange
    fingerprint = build_fingerprint("onde posso comer?", config)

    # Act / Assert
    with pytest.raises(ValueError):
        fingerprint.normalized_text = "other"
