"""Pinecone repository result models.

These model the typed outputs returned by :class:`PineconeVectorRepository`.
They live in the infrastructure layer because they describe the vector-store
query contract rather than a core domain concept.
"""

from pydantic import BaseModel


class VectorMatch(BaseModel):
    """A single similarity match returned by a vector query.

    ``score`` is the cosine similarity reported by Pinecone; only matches above
    the configured threshold are surfaced. ``text`` and ``user_code`` come from
    the stored metadata.
    """

    id: str
    score: float
    text: str
    user_code: str
