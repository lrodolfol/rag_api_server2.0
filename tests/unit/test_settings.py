"""Unit tests for the typed configuration loader."""

import pytest

from app.infrastructure.config import settings as settings_module
from app.infrastructure.config.settings import (
    MissingEnvironmentVariableError,
    get_settings,
)


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch):
    """Make settings loading hermetic: no real .env, no cross-test caching."""
    monkeypatch.setattr(settings_module, "load_dotenv", lambda *args, **kwargs: None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPEN_IA_API_KEY", "openai-key")
    monkeypatch.setenv("DATA_BASE_HOST", "db-host")
    monkeypatch.setenv("DATA_BASE_PASSWORD", "db-password")
    monkeypatch.setenv("REDIS_PASSWORD", "redis-password")
    monkeypatch.setenv("CLOUD_ACCESS_KEY", "access-key")
    monkeypatch.setenv("CLOUD_SECRET_KEY", "secret-key")


def test_should_load_dev_settings_and_resolve_secrets_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    _set_required_secrets(monkeypatch)

    # Act
    result = get_settings()

    # Assert
    assert result.environment == "dev"
    assert result.open_ai.api_key == "openai-key"
    assert result.database.host == "db-host"
    assert result.database.password == "db-password"
    assert result.bucket.access_key == "access-key"
    assert result.bucket.secret_key == "secret-key"


def test_should_keep_non_sensitive_values_from_config_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    _set_required_secrets(monkeypatch)

    # Act
    result = get_settings()

    # Assert
    assert result.open_ai.model_embeddings == "text-embedding-ada-002"
    assert result.database.port == "5432"
    assert result.redis.db == 0
    assert result.company.name == "TI NOS NEGOCIOS"


def test_should_select_environment_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "prod")
    _set_required_secrets(monkeypatch)

    # Act
    result = get_settings()

    # Assert
    assert result.environment == "prod"


def test_should_default_to_dev_when_environment_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    _set_required_secrets(monkeypatch)

    # Act
    result = get_settings()

    # Assert
    assert result.environment == "dev"


def test_should_raise_when_required_secret_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")
    _set_required_secrets(monkeypatch)
    monkeypatch.delenv("OPEN_IA_API_KEY", raising=False)

    # Act / Assert
    with pytest.raises(MissingEnvironmentVariableError):
        get_settings()
