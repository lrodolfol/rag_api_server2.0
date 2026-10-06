"""Domain layer.

Holds the business models and exceptions shared across the application. This
package must stay free of framework and infrastructure dependencies (FastAPI,
boto3, HTTP/provider clients) so the domain remains independently testable.
"""

from app.domain.company import CompanyData, CompanyRegistrationRequest
from app.domain.conversation import (
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
)
from app.domain.embedding import EmbeddingRecord
from app.domain.exceptions import (
    DomainError,
    InappropriateContentError,
    OpenIaException,
    RateLimitError,
)
from app.domain.search import OnlineChatSearchPayload, WhatsAppSearchPayload

__all__ = [
    "CompanyData",
    "CompanyRegistrationRequest",
    "DomainError",
    "EmbeddingRecord",
    "InappropriateContentError",
    "MessageHistoryItem",
    "MessageRole",
    "OnlineChatSearchPayload",
    "OpenIaException",
    "PayloadQuestionOpenIA",
    "RateLimitError",
    "WhatsAppSearchPayload",
]
