"""Text processing package.

Exposes the normalisation and chunking helpers used to prepare client text
before embeddings are generated, and the short-message detector used to answer
content-less messages without calling the language model.
"""

from app.application.text_processing.message_validator import (
    MIN_MESSAGE_LETTERS,
    is_short_message,
)
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
    "MIN_MESSAGE_LETTERS",
    "generate_chunks",
    "is_short_message",
    "normalize_text",
]
