"""Unit tests for the typed configuration models."""

import pytest
from pydantic import ValidationError

from app.infrastructure.config import (
    CategoriesConfig,
    EmbeddingModelConfig,
    FingerPrintConfig,
    OpenAIConfig,
    PostgresConfig,
    SemanticCacheConfig,
)


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


FINGER_PRINT_FIELDS: dict[str, str] = {
    "prompt_version": "1.0.0",
    "rules_version": "1.0.0",
    "model_capability": "economic",
}


@pytest.mark.parametrize("missing_field", list(FINGER_PRINT_FIELDS))
def test_should_reject_finger_print_config_with_missing_field(
    missing_field: str,
) -> None:
    # Arrange
    fields = {k: v for k, v in FINGER_PRINT_FIELDS.items() if k != missing_field}

    # Act / Assert
    with pytest.raises(ValidationError, match=missing_field):
        FingerPrintConfig(**fields)


@pytest.mark.parametrize("empty_field", list(FINGER_PRINT_FIELDS))
def test_should_reject_finger_print_config_with_empty_field(empty_field: str) -> None:
    # Arrange
    fields = {**FINGER_PRINT_FIELDS, empty_field: ""}

    # Act / Assert
    with pytest.raises(ValidationError, match=empty_field):
        FingerPrintConfig(**fields)


POSTGRES_FIELDS: dict[str, str | int] = {
    "host": "localhost",
    "port": 5432,
    "database": "rag_auth",
    "user": "postgres",
    "password": "postgres-secret",
}

SEMANTIC_CACHE_FIELDS: dict[str, str | int] = {
    "table": "rag_response_cache",
    "top_k": 3,
}


def test_should_build_postgres_config_with_all_fields() -> None:
    # Act
    config = PostgresConfig(**POSTGRES_FIELDS)

    # Assert
    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "rag_auth"
    assert config.user == "postgres"
    assert config.password.get_secret_value() == "postgres-secret"


@pytest.mark.parametrize("missing_field", list(POSTGRES_FIELDS))
def test_should_reject_postgres_config_with_missing_field(missing_field: str) -> None:
    # Arrange
    fields = {k: v for k, v in POSTGRES_FIELDS.items() if k != missing_field}

    # Act / Assert
    with pytest.raises(ValidationError, match=missing_field):
        PostgresConfig(**fields)


def test_should_mask_postgres_password_in_repr() -> None:
    # Act
    config = PostgresConfig(**POSTGRES_FIELDS)

    # Assert
    assert "postgres-secret" not in repr(config)
    assert "postgres-secret" not in str(config)


@pytest.mark.parametrize("missing_field", list(SEMANTIC_CACHE_FIELDS))
def test_should_reject_semantic_cache_config_with_missing_field(
    missing_field: str,
) -> None:
    # Arrange
    fields = {k: v for k, v in SEMANTIC_CACHE_FIELDS.items() if k != missing_field}

    # Act / Assert
    with pytest.raises(ValidationError, match=missing_field):
        SemanticCacheConfig(**fields)


def test_should_reject_semantic_cache_config_with_empty_table() -> None:
    # Arrange
    fields = {**SEMANTIC_CACHE_FIELDS, "table": ""}

    # Act / Assert
    with pytest.raises(ValidationError, match="table"):
        SemanticCacheConfig(**fields)


@pytest.mark.parametrize("top_k", [0, -1])
def test_should_reject_semantic_cache_config_with_non_positive_top_k(
    top_k: int,
) -> None:
    # Arrange
    fields = {**SEMANTIC_CACHE_FIELDS, "top_k": top_k}

    # Act / Assert
    with pytest.raises(ValidationError, match="top_k"):
        SemanticCacheConfig(**fields)


def _categories_data(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "redis_key": "knowledge_categories",
        "initial": ["ALIMENTAÇÃO", "SAÚDE"],
        "fallback": "OUTROS",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("field", ["redis_key", "initial", "fallback"])
def test_should_require_every_categories_field(field: str) -> None:
    # Arrange
    data = _categories_data()
    del data[field]

    # Act / Assert
    with pytest.raises(ValidationError, match=field):
        CategoriesConfig(**data)


@pytest.mark.parametrize(
    ("field", "value"),
    [("redis_key", ""), ("redis_key", "  "), ("initial", []), ("fallback", ""), ("fallback", "  ")],
)
def test_should_reject_empty_categories_fields(field: str, value: object) -> None:
    # Act / Assert
    with pytest.raises(ValidationError, match=field):
        CategoriesConfig(**_categories_data(**{field: value}))


def test_should_reject_blank_initial_category_name() -> None:
    # Act / Assert
    with pytest.raises(ValidationError, match="must not be blank"):
        CategoriesConfig(**_categories_data(initial=["SAÚDE", "  "]))
