"""Text processing package.

Exposes the normalisation and chunking helpers used to prepare client text
before embeddings are generated.
"""

from app.application.text_processing.text_processor import (
    CHUNK_OVERLAP,
    CHUNK_SEPARATORS,
    CHUNK_SIZE,
    generate_chunks,
    normalize_text,
)

__all__ = [
    "CHUNK_OVERLAP",
    "CHUNK_SEPARATORS",
    "CHUNK_SIZE",
    "generate_chunks",
    "normalize_text",
]
