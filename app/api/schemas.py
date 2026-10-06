"""API boundary schemas.

The request/response shapes accepted and returned by the HTTP layer are the
domain models themselves, re-exported here so routes depend on a single,
stable import point without the domain layer learning about FastAPI. The shared
:class:`ApiResponse` envelope is exposed alongside them for convenience.
"""

from app.api.patterns.response import ApiResponse
from app.domain import (
    CompanyData,
    CompanyRegistrationRequest,
    OnlineChatSearchPayload,
    WhatsAppSearchPayload,
)

__all__ = [
    "ApiResponse",
    "CompanyData",
    "CompanyRegistrationRequest",
    "OnlineChatSearchPayload",
    "WhatsAppSearchPayload",
]
