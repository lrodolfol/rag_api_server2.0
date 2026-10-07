"""Pinecone client factory.

Isolates construction of the third-party :class:`pinecone.Pinecone` client so
the repository depends on an injected client instance, keeping it unit-testable
without touching the network.

The API key is read from the typed configuration, never hardcoded or logged.
"""

from pinecone import Pinecone

from app.infrastructure.config import PineconeConfig


def create_pinecone_client(config: PineconeConfig) -> Pinecone:
    """Build a :class:`Pinecone` client from the application configuration."""
    return Pinecone(api_key=config.api_key.get_secret_value())
