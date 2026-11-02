"""Answer-cache domain models.

The fingerprint is the set of values that uniquely identifies a cached answer:
the prompt and business-rule versions, the configured model capability and the
normalized question. Any change in one of them yields a different cache key.

The semantic cache stores answers together with the embedding of the normalized
question, so semantically similar questions can reuse a previous answer.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CacheFingerprint(BaseModel):
    """Immutable identity of a question for the answer cache."""

    model_config = ConfigDict(frozen=True)

    prompt_version: str
    rules_version: str
    model_capability: str
    normalized_text: str


class SemanticCacheEntry(BaseModel):
    """Immutable answer record persisted in the semantic cache."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    fingerprint: CacheFingerprint
    input_text: str
    response: str
    embedding: list[float]
    created_at: datetime


class SemanticCacheMatch(BaseModel):
    """Immutable semantic cache lookup result (``distance`` is cosine distance)."""

    model_config = ConfigDict(frozen=True)

    input_text: str
    response: str
    distance: float
    similarity: float
