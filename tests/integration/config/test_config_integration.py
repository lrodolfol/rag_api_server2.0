"""Integration tests: load the real ``env.example.json`` with test env vars.

These tests exercise the full path (real configuration file on disk + secrets
injected from environment variables) to validate the end-to-end wiring.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.infrastructure.config import AppConfig, ConfigError, get_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_CONFIG = PROJECT_ROOT / "env.example.json"

SECRET_VALUES: dict[str, str] = {
    "OPEN_IA_API_KEY": "integration-openai",
    "PINECONE_API_KEY": "integration-pinecone",
    "REDIS_PASSWORD": "integration-redis",
    "CLOUD_ACCESS_KEY": "integration-access",
    "CLOUD_SECRET_KEY": "integration-secret",
    "DATA_BASE_PASSWORD": "integration-postgres",
}


@pytest.fixture(autouse=True)
def _prepare_environment(monkeypatch: pytest.MonkeyPatch) -> Any:
    get_config.cache_clear()
    monkeypatch.setenv("CONFIG_FILE", str(EXAMPLE_CONFIG))
    for env_var, value in SECRET_VALUES.items():
        monkeypatch.setenv(env_var, value)
    yield
    get_config.cache_clear()


def test_should_load_dev_config_from_real_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")

    # Act
    config = get_config()

    # Assert
    assert isinstance(config, AppConfig)
    assert config.environment == "dev"
    assert config.pinecone.index_name == "acha-local-services-dev"
    assert config.pinecone.environment == "development"
    assert config.pinecone.dimension == 1536
    assert config.redis.port == 6379
    assert config.company.name == "TI NOS NEGOCIOS"
    assert config.bucket.name == "tnn-rag"


def test_should_load_prod_config_from_real_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "prod")

    # Act
    config = get_config()

    # Assert
    assert config.environment == "prod"
    assert config.pinecone.index_name == "acha-local-services-prod"
    assert config.pinecone.environment == "production"


def test_should_inject_all_secrets_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", "dev")

    # Act
    config = get_config()

    # Assert
    assert config.open_ai.api_key.get_secret_value() == "integration-openai"
    assert config.pinecone.api_key.get_secret_value() == "integration-pinecone"
    assert config.redis.password.get_secret_value() == "integration-redis"
    assert config.bucket.access_key.get_secret_value() == "integration-access"
    assert config.bucket.secret_key.get_secret_value() == "integration-secret"
    assert config.postgres.password.get_secret_value() == "integration-postgres"


def test_example_file_contains_no_real_secrets() -> None:
    # Arrange / Act
    content = EXAMPLE_CONFIG.read_text(encoding="utf-8")

    # Assert: placeholders only, never injected test values.
    assert content.count("get from environment") == 12
    for value in SECRET_VALUES.values():
        assert value not in content


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_should_resolve_default_embedding_model_from_real_file(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", environment)

    # Act
    config = get_config()

    # Assert
    assert set(config.open_ai.models) == {"economic", "stronger"}
    assert config.open_ai.default_model_embeddings == "text-embedding-3-small"


@pytest.mark.parametrize("environment", ["dev", "prod"])
@pytest.mark.parametrize("config_file", ["env.example.json", "env.json"])
def test_should_load_finger_print_from_real_file(
    monkeypatch: pytest.MonkeyPatch, environment: str, config_file: str
) -> None:
    # Arrange
    path = PROJECT_ROOT / config_file
    if not path.exists():
        pytest.skip(f"{config_file} not present in this checkout")
    monkeypatch.setenv("CONFIG_FILE", str(path))
    monkeypatch.setenv("ENVIRONMENT", environment)

    # Act
    config = get_config()

    # Assert
    assert config.finger_print.prompt_version
    assert config.finger_print.rules_version
    assert config.finger_print.model_capability


@pytest.mark.parametrize("environment", ["dev", "prod"])
@pytest.mark.parametrize("config_file", ["env.example.json", "env.json"])
def test_should_load_postgres_and_semantic_cache_from_real_file(
    monkeypatch: pytest.MonkeyPatch, environment: str, config_file: str
) -> None:
    # Arrange
    path = PROJECT_ROOT / config_file
    if not path.exists():
        pytest.skip(f"{config_file} not present in this checkout")
    monkeypatch.setenv("CONFIG_FILE", str(path))
    monkeypatch.setenv("ENVIRONMENT", environment)

    # Act
    config = get_config()

    # Assert
    assert config.postgres.host
    assert config.postgres.port > 0
    assert config.postgres.database
    assert config.postgres.user
    assert config.postgres.password.get_secret_value() == "integration-postgres"
    assert config.semantic_cache.table
    assert config.semantic_cache.top_k > 0


EXPECTED_INITIAL_CATEGORIES: list[str] = [
    "ALIMENTAÇÃO",
    "SAÚDE",
    "BELEZA",
    "CONSTRUÇÃO",
    "AUTOMOTIVO",
    "TECNOLOGIA",
    "COMÉRCIO",
    "EDUCAÇÃO",
    "SERVIÇOS PROFISSIONAIS",
    "TRANSPORTE",
    "CASA E MANUTENÇÃO",
    "ANIMAIS",
    "EVENTOS",
    "TURISMO",
    "ENTRETENIMENTO",
    "MODA",
    "FINANCEIRO",
    "AGROPECUÁRIA",
    "RELIGIÃO",
    "SERVIÇOS PÚBLICOS",
]


@pytest.mark.parametrize("environment", ["dev", "prod"])
@pytest.mark.parametrize("config_file", ["env.example.json", "env.json"])
def test_should_load_the_20_initial_categories_from_real_file(
    monkeypatch: pytest.MonkeyPatch, environment: str, config_file: str
) -> None:
    # Arrange
    path = PROJECT_ROOT / config_file
    if not path.exists():
        pytest.skip(f"{config_file} not present in this checkout")
    monkeypatch.setenv("CONFIG_FILE", str(path))
    monkeypatch.setenv("ENVIRONMENT", environment)

    # Act
    config = get_config()

    # Assert
    assert config.categories.initial == EXPECTED_INITIAL_CATEGORIES
    assert config.categories.redis_key == "knowledge_categories"
    assert config.categories.fallback == "OUTROS"


def test_should_raise_when_categories_removed_from_real_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    data = json.loads(EXAMPLE_CONFIG.read_text(encoding="utf-8"))
    del data["dev"]["categories"]
    broken_file = tmp_path / "env.json"
    broken_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("CONFIG_FILE", str(broken_file))
    monkeypatch.setenv("ENVIRONMENT", "dev")

    # Act / Assert
    with pytest.raises(ConfigError, match="categories"):
        get_config()
