"""Domain layer.

Holds the business models and exceptions shared across the application. This
package must stay free of framework and infrastructure dependencies (FastAPI,
boto3, HTTP/provider clients) so the domain remains independently testable.
"""

from app.domain.answer import ChatAnswer
from app.domain.cache import (
    CacheFingerprint,
    SemanticCacheEntry,
    SemanticCacheMatch,
)
from app.domain.category import Category, slugify
from app.domain.company import (
    CompanyData,
    CompanyDeletionRequest,
    CompanyRegistrationRequest,
)
from app.domain.conversation import (
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
)
from app.domain.embedding import EmbeddingRecord
from app.domain.exceptions import (
    ClientStorageError,
    DomainError,
    HistoryStoreError,
    InappropriateContentError,
    InvalidChatAnswerError,
    OpenIaException,
    RateLimitError,
    VectorRepositoryError,
)
from app.domain.prompts import INPUT_GUIDE, QUERY_PREFIX
from app.domain.search import OnlineChatSearchPayload, WhatsAppSearchPayload

__all__ = [
    "CacheFingerprint",
    "Category",
    "ChatAnswer",
    "ClientStorageError",
    "CompanyData",
    "CompanyDeletionRequest",
    "CompanyRegistrationRequest",
    "DomainError",
    "EmbeddingRecord",
    "HistoryStoreError",
    "InappropriateContentError",
    "INPUT_GUIDE",
    "InvalidChatAnswerError",
    "MessageHistoryItem",
    "MessageRole",
    "OnlineChatSearchPayload",
    "OpenIaException",
    "PayloadQuestionOpenIA",
    "QUERY_PREFIX",
    "RateLimitError",
    "SemanticCacheEntry",
    "SemanticCacheMatch",
    "VectorRepositoryError",
    "WhatsAppSearchPayload",
    "slugify",
]
