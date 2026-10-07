"""Pinecone integration package.

Exposes the async vector repository used by the RAG pipeline, the factory that
builds the underlying provider client from the typed configuration, and the
typed query-result model.
"""

from app.infrastructure.pinecone.client import create_pinecone_client
from app.infrastructure.pinecone.models import VectorMatch
from app.infrastructure.pinecone.repository import (
    DEFAULT_TOP_K,
    SIMILARITY_THRESHOLD,
    PineconeVectorRepository,
)

__all__ = [
    "DEFAULT_TOP_K",
    "SIMILARITY_THRESHOLD",
    "PineconeVectorRepository",
    "VectorMatch",
    "create_pinecone_client",
]
