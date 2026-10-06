"""Unit tests for the configuration loader and secret resolution."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.infrastructure.config import AppConfig, ConfigError, get_config
from app.infrastructure.config.loader import SECRET_ENV_VARS

SECRET_VALUES: dict[str, str] = {
    "OPEN_IA_API_KEY": "openai-secret",
    "PINECONE_API_KEY": "pinecone-secret",
    "REDIS_PASSWORD": "redis-secret",
    "CLOUD_ACCESS_KEY": "bucket-access-secret",
    "CLOUD_SECRET_KEY": "bucket-secret-secret",
}


def _section(index_name: str, env_label: str) -> dict[str, Any]:
    """Build one environment section with secret placeholders."""
    return {
        "open_ai": {
            "api_key": "get from environment",
            "model_embeddings": "text-embedding-ada-002",
            "model_chat": "gpt-3.5-turbo",
            "input_guide": "guide",
        },
        "pinecone": {
            "api_key": "get from environment",
            "index_name": index_name,
            "region": "us-east-1",
            "environment": env_label,
            "metric": "cosine",
            "vector_type": "dense",
            "dimension": 1536,
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": "get from environment",
        },
        "company": {
            "name": "TI NOS NEGOCIOS",
            "email": "company@example.com",
            "ceo": {
                "name": "CEO",
                "person_email": "ceo@example.com",
                "professional_email": "ceo@company.com",
            },
        },
        "bucket": {
            "name": "tnn-rag",
            "bucket_name": "acha-local",
            "access_key": "get from environment",
            "secret_key": "get from environment",
            "region": "us-east-1",
        },
    }


def _write_config(path: Path, data: dict[str, Any]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    data = {
        "dev": _section("acha-local-services-dev", "development"),
        "prod": _section("acha-local-services-prod", "production"),
    }
    return _write_config(tmp_path / "env.json", data)


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    get_config.cache_clear()
    yield
    get_config.cache_clear()


@pytest.fixture
def _set_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var, value in SECRET_VALUES.items():
        monkeypatch.setenv(env_var, value)


def test_should_load_config_for_dev_environment(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act
    config = get_config()

    # Assert
    assert isinstance(config, AppConfig)
    assert config.environment == "dev"
    assert config.pinecone.index_name == "acha-local-services-dev"


def test_should_load_config_for_prod_environment(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act
    config = get_config()

    # Assert
    assert config.environment == "prod"
    assert config.pinecone.index_name == "acha-local-services-prod"


def test_should_default_to_dev_when_environment_not_set(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act
    config = get_config()

    # Assert
    assert config.environment == "dev"


def test_should_resolve_secrets_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act
    config = get_config()

    # Assert
    assert config.open_ai.api_key.get_secret_value() == "openai-secret"
    assert config.pinecone.api_key.get_secret_value() == "pinecone-secret"
    assert config.redis.password.get_secret_value() == "redis-secret"
    assert config.bucket.access_key.get_secret_value() == "bucket-access-secret"
    assert config.bucket.secret_key.get_secret_value() == "bucket-secret-secret"


def test_should_ignore_secret_value_present_in_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, _set_secrets: None
) -> None:
    # Arrange: file carries a fake hardcoded secret that must be overridden.
    data = {"dev": _section("acha-local-services-dev", "development")}
    data["dev"]["open_ai"]["api_key"] = "hardcoded-in-file"
    config_path = _write_config(tmp_path / "env.json", data)
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_path))

    # Act
    config = get_config()

    # Assert
    assert config.open_ai.api_key.get_secret_value() == "openai-secret"


def test_should_mask_secrets_in_repr(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act
    config = get_config()

    # Assert
    assert "openai-secret" not in repr(config)
    assert "redis-secret" not in repr(config)


@pytest.mark.parametrize("missing_var", sorted(set(SECRET_ENV_VARS.values())))
def test_should_raise_when_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
    config_file: Path,
    _set_secrets: None,
    missing_var: str,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))
    monkeypatch.delenv(missing_var, raising=False)

    # Act / Assert
    with pytest.raises(ConfigError, match=missing_var):
        get_config()


def test_should_raise_when_config_file_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(tmp_path / "does_not_exist.json"))

    # Act / Assert
    with pytest.raises(ConfigError, match="Configuration file not found"):
        get_config()


def test_should_raise_when_environment_not_in_file(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))

    # Act / Assert
    with pytest.raises(ConfigError, match="staging"):
        get_config()


def test_should_raise_when_json_is_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, _set_secrets: None
) -> None:
    # Arrange
    broken = tmp_path / "env.json"
    broken.write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(broken))

    # Act / Assert
    with pytest.raises(ConfigError, match="Invalid JSON"):
        get_config()


def test_should_cache_config_and_not_reread_file(
    monkeypatch: pytest.MonkeyPatch, config_file: Path, _set_secrets: None
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("CONFIG_FILE", str(config_file))
    first = get_config()

    # Act: mutate the file after the first load; the cache must shield it.
    mutated = {"dev": _section("mutated-index", "development")}
    _write_config(config_file, mutated)
    second = get_config()

    # Assert
    assert second is first
    assert second.pinecone.index_name == "acha-local-services-dev"
