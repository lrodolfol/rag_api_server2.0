"""Typed application configuration loader.

Loads a per-environment JSON file (``dev``/``prod``) and resolves every
sensitive value from environment variables. Non-sensitive values live in the
JSON files; secrets never do (they carry the ``get from environment``
placeholder and are filled from the process environment / ``.env``).
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

CONFIG_DIR = Path(__file__).resolve().parent
SECRET_PLACEHOLDER = "get from environment"
DEFAULT_ENVIRONMENT = "dev"

# Maps "<section>.<field>" in the JSON config to the environment variable that
# must provide its value. Every sensitive field is listed here explicitly.
SECRET_ENV_MAP: dict[str, str] = {
    "open_ai.api_key": "OPEN_IA_API_KEY",
    "database.host": "DATA_BASE_HOST",
    "database.password": "DATA_BASE_PASSWORD",
    "redis.password": "REDIS_PASSWORD",
    "bucket.access_key": "CLOUD_ACCESS_KEY",
    "bucket.secret_key": "CLOUD_SECRET_KEY",
}


class MissingEnvironmentVariableError(RuntimeError):
    """Raised when a required secret is not present in the environment."""


class OpenAIConfig(BaseModel):
    api_key: str
    model_embeddings: str
    model_chat: str
    input_guide: str


class DatabaseConfig(BaseModel):
    host: str
    port: str
    database: str
    user: str
    password: str


class RedisConfig(BaseModel):
    host: str
    port: str
    db: int
    password: str


class CeoConfig(BaseModel):
    name: str
    person_email: str
    professional_email: str


class CompanyConfig(BaseModel):
    name: str
    email: str
    ceo: CeoConfig


class BucketConfig(BaseModel):
    name: str
    host: str
    access_key: str
    secret_key: str
    region: str


class Settings(BaseModel):
    environment: str
    open_ai: OpenAIConfig
    database: DatabaseConfig
    redis: RedisConfig
    company: CompanyConfig
    bucket: BucketConfig


def _read_config_file(environment: str) -> dict:
    config_path = CONFIG_DIR / f"{environment}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with config_path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def _resolve_secret(path: str, env_var: str) -> str:
    value = os.getenv(env_var)
    if not value:
        raise MissingEnvironmentVariableError(
            f"Environment variable '{env_var}' required for '{path}' is not set."
        )
    return value


def _apply_secrets(raw_config: dict) -> dict:
    for path, env_var in SECRET_ENV_MAP.items():
        section, field = path.split(".")
        if raw_config.get(section, {}).get(field) == SECRET_PLACEHOLDER:
            raw_config[section][field] = _resolve_secret(path, env_var)
    return raw_config


@lru_cache
def get_settings() -> Settings:
    """Load and cache the typed settings for the active environment."""
    load_dotenv()
    environment = os.getenv("ENVIRONMENT", DEFAULT_ENVIRONMENT).strip().lower()
    raw_config = _apply_secrets(_read_config_file(environment))
    return Settings(environment=environment, **raw_config)
