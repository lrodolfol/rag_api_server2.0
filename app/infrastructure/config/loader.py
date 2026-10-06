"""Configuration loader.

Loads dynamic (non-sensitive) values from ``env.json`` for the selected
environment and injects every secret exclusively from environment variables.
Secrets are never read from the configuration file.

The resolved :class:`AppConfig` is cached so the file is read and validated only
once per process; call :func:`get_config.cache_clear` to force a reload (mainly
useful in tests).
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Final

from app.infrastructure.config.models import AppConfig

ENVIRONMENT_VAR: Final[str] = "ENVIRONMENT"
CONFIG_FILE_VAR: Final[str] = "CONFIG_FILE"
DEFAULT_ENVIRONMENT: Final[str] = "dev"
CONFIG_FILE_NAME: Final[str] = "env.json"
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]

# (section, field) -> environment variable holding the secret value.
SECRET_ENV_VARS: Final[dict[tuple[str, str], str]] = {
    ("open_ai", "api_key"): "OPEN_IA_API_KEY",
    ("pinecone", "api_key"): "PINECONE_API_KEY",
    ("redis", "password"): "REDIS_PASSWORD",
    ("bucket", "access_key"): "CLOUD_ACCESS_KEY",
    ("bucket", "secret_key"): "CLOUD_SECRET_KEY",
}


class ConfigError(Exception):
    """Raised when the application configuration cannot be loaded."""


def _config_path() -> Path:
    """Resolve the configuration file path, honouring a ``CONFIG_FILE`` override."""
    override = os.getenv(CONFIG_FILE_VAR)
    if override:
        return Path(override)
    return PROJECT_ROOT / CONFIG_FILE_NAME


def _read_environment_section(environment: str, path: Path) -> dict:
    """Read and return the raw section for ``environment`` from the config file."""
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ConfigError(f"Invalid JSON in configuration file: {path}") from error

    if environment not in data:
        raise ConfigError(
            f"Environment '{environment}' not found in configuration file"
        )
    return data[environment]


def _inject_secrets(section_data: dict) -> dict:
    """Overwrite each secret field with its value from the environment.

    Any missing secret fails loudly so misconfiguration is detected at startup.
    """
    for (section, field), env_var in SECRET_ENV_VARS.items():
        if section not in section_data:
            raise ConfigError(f"Missing configuration section: '{section}'")

        secret_value = os.getenv(env_var)
        if not secret_value:
            raise ConfigError(
                f"Missing required secret environment variable: '{env_var}'"
            )
        section_data[section][field] = secret_value
    return section_data


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the validated application configuration (loaded once and cached)."""
    environment = os.getenv(ENVIRONMENT_VAR, DEFAULT_ENVIRONMENT)
    raw_section = _read_environment_section(environment, _config_path())
    raw_section["environment"] = environment
    return AppConfig(**_inject_secrets(raw_section))
