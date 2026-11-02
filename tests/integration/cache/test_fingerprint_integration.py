"""Integration tests: build cache keys from the real ``env.example.json``."""

import re
from pathlib import Path
from typing import Iterator

import pytest

from app.application.cache import build_cache_key, build_fingerprint
from app.infrastructure.config import get_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_CONFIG = PROJECT_ROOT / "env.example.json"
SECRET_ENV_VARS = (
    "OPEN_IA_API_KEY",
    "PINECONE_API_KEY",
    "REDIS_PASSWORD",
    "CLOUD_ACCESS_KEY",
    "CLOUD_SECRET_KEY",
    "DATA_BASE_PASSWORD",
)


@pytest.fixture(autouse=True)
def _prepare_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_config.cache_clear()
    monkeypatch.setenv("CONFIG_FILE", str(EXAMPLE_CONFIG))
    for env_var in SECRET_ENV_VARS:
        monkeypatch.setenv(env_var, "integration-secret")
    yield
    get_config.cache_clear()


@pytest.mark.parametrize("environment", ["dev", "prod"])
def test_should_build_cache_key_from_real_config(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    # Arrange
    monkeypatch.setenv("ENVIRONMENT", environment)
    config = get_config().finger_print

    # Act
    fingerprint = build_fingerprint("Onde posso COMER?", config)
    key = build_cache_key(fingerprint)

    # Assert
    assert fingerprint.model_capability == config.model_capability
    assert re.fullmatch(r"[0-9a-f]{64}", key)
    assert key == build_cache_key(build_fingerprint("onde posso comer?", config))
