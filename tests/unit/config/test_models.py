"""Unit tests for the typed configuration models."""

import pytest
from pydantic import ValidationError

from app.infrastructure.config import EmbeddingModelConfig, OpenAIConfig


def _openai_config(models: dict[str, EmbeddingModelConfig]) -> OpenAIConfig:
    return OpenAIConfig(api_key="secret", models=models, model_chat="chat-model")


def test_should_return_the_only_default_embedding_model() -> None:
    # Arrange
    config = _openai_config(
        {
            "economic": EmbeddingModelConfig(default=True, model_embeddings="small"),
            "stronger": EmbeddingModelConfig(default=False, model_embeddings="large"),
        }
    )

    # Act
    model = config.default_model_embeddings

    # Assert
    assert model == "small"


def test_should_return_first_default_when_many_are_default() -> None:
    # Arrange
    config = _openai_config(
        {
            "stronger": EmbeddingModelConfig(default=True, model_embeddings="large"),
            "economic": EmbeddingModelConfig(default=True, model_embeddings="small"),
        }
    )

    # Act
    model = config.default_model_embeddings

    # Assert
    assert model == "large"


def test_should_skip_non_default_models_listed_first() -> None:
    # Arrange
    config = _openai_config(
        {
            "economic": EmbeddingModelConfig(default=False, model_embeddings="small"),
            "stronger": EmbeddingModelConfig(default=True, model_embeddings="large"),
        }
    )

    # Act
    model = config.default_model_embeddings

    # Assert
    assert model == "large"


def test_should_reject_models_without_default() -> None:
    # Arrange
    models = {"economic": EmbeddingModelConfig(default=False, model_embeddings="small")}

    # Act / Assert
    with pytest.raises(ValidationError, match="must be marked as default"):
        _openai_config(models)


def test_should_reject_empty_models() -> None:
    # Act / Assert
    with pytest.raises(ValidationError, match="must be marked as default"):
        _openai_config({})
