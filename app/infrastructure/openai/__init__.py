"""OpenAI integration package.

Exposes the async service used by the RAG pipeline and the factory that builds
the underlying provider client from the typed configuration.
"""

from app.infrastructure.openai.client import (
    DEFAULT_TIMEOUT_SECONDS,
    create_openai_client,
)
from app.infrastructure.openai.models import ModerationResult
from app.infrastructure.openai.service import OpenAIService

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "ModerationResult",
    "OpenAIService",
    "create_openai_client",
]
