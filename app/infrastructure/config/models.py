"""Typed configuration models.

Each application concern (OpenAI, Pinecone, Redis, PostgreSQL, company, bucket,
semantic cache) is modelled as its own section so the rest of the codebase
depends on a single, validated configuration object instead of reading
environment data ad hoc.

Secrets use ``pydantic.SecretStr`` so their values are masked in logs, ``repr``
and tracebacks, preventing accidental leakage of sensitive data.
"""

from typing import Self

from pydantic import BaseModel, Field, SecretStr, model_validator


class EmbeddingModelConfig(BaseModel):
    """One named embedding model option."""

    default: bool
    model_embeddings: str


class OpenAIConfig(BaseModel):
    """OpenAI client configuration.

    ``models`` holds every available embedding model; the one in use is the
    first (in file order) flagged as ``default``.
    """

    api_key: SecretStr
    models: dict[str, EmbeddingModelConfig]
    model_chat: str

    @model_validator(mode="after")
    def _ensure_default_model(self) -> Self:
        if not any(model.default for model in self.models.values()):
            raise ValueError("At least one embedding model must be marked as default")
        return self

    @property
    def default_model_embeddings(self) -> str:
        """Return the first embedding model flagged as ``default``."""
        return next(
            model.model_embeddings for model in self.models.values() if model.default
        )


class PineconeConfig(BaseModel):
    """Pinecone vector database configuration."""

    api_key: SecretStr
    index_name: str
    region: str
    environment: str
    metric: str
    vector_type: str
    dimension: int


class RedisConfig(BaseModel):
    """Redis connection configuration."""

    host: str
    port: int
    db: int
    password: SecretStr


class CeoConfig(BaseModel):
    """Company representative contact details."""

    name: str
    person_email: str
    professional_email: str


class CompanyConfig(BaseModel):
    """Owning company metadata used across the application."""

    name: str
    email: str
    ceo: CeoConfig


class BucketConfig(BaseModel):
    """Object storage (S3-compatible) bucket configuration.

    ``host`` and ``bucket_name`` are optional because they vary between
    environments (local emulator vs. managed storage).
    """

    name: str
    access_key: SecretStr
    secret_key: SecretStr
    region: str
    host: str | None = None
    bucket_name: str | None = None


class FingerPrintConfig(BaseModel):
    """Versions that compose the answer-cache fingerprint.

    Bumping any value changes every cache key, which is how cached answers are
    invalidated manually. ``model_capability`` is used as-is (e.g. ``economic``).
    """

    prompt_version: str = Field(min_length=1)
    rules_version: str = Field(min_length=1)
    model_capability: str = Field(min_length=1)


class PostgresConfig(BaseModel):
    """PostgreSQL connection configuration (semantic cache storage)."""

    host: str
    port: int
    database: str
    user: str
    password: SecretStr


class SemanticCacheConfig(BaseModel):
    """Semantic cache query parameters.

    ``table`` is the pgvector table holding cached answers and ``top_k`` the
    number of nearest neighbours returned by each lookup.
    """

    table: str = Field(min_length=1)
    top_k: int = Field(gt=0)


class AppConfig(BaseModel):
    """Root configuration object aggregating every section."""

    environment: str
    open_ai: OpenAIConfig
    pinecone: PineconeConfig
    redis: RedisConfig
    company: CompanyConfig
    bucket: BucketConfig
    finger_print: FingerPrintConfig
    postgres: PostgresConfig
    semantic_cache: SemanticCacheConfig
