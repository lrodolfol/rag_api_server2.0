"""Embedding domain model.

Represents a single chunk of text together with the vector produced for it. It
is deliberately provider-agnostic: how the vector is generated (OpenAI, etc.)
is an infrastructure concern that lives outside the domain.
"""

from pydantic import BaseModel, Field


class EmbeddingRecord(BaseModel):
    """A text chunk paired with its embedding vector."""

    text: str = Field(min_length=1)
    vector: list[float]
