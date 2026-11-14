"""Answer-cache domain models.

The fingerprint is the set of values that uniquely identifies a cached answer:
the prompt and business-rule versions, the configured model capability and the
normalized question. Any change in one of them yields a different cache key.

The semantic cache stores answers together with the embedding of the normalized
question, so semantically similar questions can reuse a previous answer. Each
entry also carries the slug of the category the question was classified into
(``None`` when the search ran without a category filter), so the entries of a
category can be invalidated when one of its services changes. A lookup match
carries that category too, so an answer reused from the semantic cache can be
indexed under the categories it came from.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    # Category slug of the question; ``None`` when the search ran without a filter.
    category: str | None = Field(default=None, min_length=1)


class SemanticCacheMatch(BaseModel):
    """Immutable semantic cache lookup result (``distance`` is cosine distance)."""

    model_config = ConfigDict(frozen=True)

    input_text: str
    response: str
    distance: float
    similarity: float
    # Category slug of the matched entry; ``None`` when it has no category.
    category: str | None = Field(default=None, min_length=1)
