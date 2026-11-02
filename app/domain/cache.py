"""Answer-cache domain model.

The fingerprint is the set of values that uniquely identifies a cached answer:
the prompt and business-rule versions, the configured model capability and the
normalized question. Any change in one of them yields a different cache key.
"""

from pydantic import BaseModel, ConfigDict


class CacheFingerprint(BaseModel):
    """Immutable identity of a question for the answer cache."""

    model_config = ConfigDict(frozen=True)

    prompt_version: str
    rules_version: str
    model_capability: str
    normalized_text: str
