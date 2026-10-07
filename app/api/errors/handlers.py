"""Global API exception handlers.

Translate the domain exceptions (and any otherwise-unhandled error) into the
standard :class:`ApiResponse` envelope, so clients always receive the same
``status_code``/``message``/``errors`` shape.

Client-facing errors (:class:`InappropriateContentError`,
:class:`RateLimitError`) keep their safe, human-readable message. Every other
domain error and any unexpected exception are surfaced as a single generic
message: stack traces, provider payloads and other internal details are logged
server-side but never exposed to the client (see ``security.md`` and
``error-handling.md``).
"""

from typing import Final

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.patterns.response import ApiResponse
from app.domain import DomainError, InappropriateContentError, RateLimitError
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

INTERNAL_ERROR_MESSAGE: Final[str] = "An unexpected error occurred."
INTERNAL_ERROR_CODE: Final[str] = "internal_error"


def _envelope(status_code: int, message: str, error_code: str) -> JSONResponse:
    """Build a JSON response wrapping the standard API envelope."""
    body = ApiResponse(status_code=status_code, message=message, errors=[error_code])
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def _handle_inappropriate_content(
    _: Request, exception: InappropriateContentError
) -> JSONResponse:
    """Return a 400 envelope for content rejected by moderation."""
    return _envelope(
        status.HTTP_400_BAD_REQUEST, str(exception), "inappropriate_content"
    )


async def _handle_rate_limit(_: Request, exception: RateLimitError) -> JSONResponse:
    """Return a 429 envelope when a caller exceeds the allowed message limit."""
    return _envelope(
        status.HTTP_429_TOO_MANY_REQUESTS, str(exception), "rate_limit_exceeded"
    )


async def _handle_domain_error(_: Request, exception: DomainError) -> JSONResponse:
    """Return a safe 500 envelope for infrastructure/provider domain failures."""
    logger.exception("Unhandled domain error reached the API boundary")
    return _envelope(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        INTERNAL_ERROR_MESSAGE,
        INTERNAL_ERROR_CODE,
    )


async def _handle_unexpected_error(_: Request, exception: Exception) -> JSONResponse:
    """Return a safe 500 envelope for any otherwise-unhandled exception."""
    logger.exception("Unexpected error reached the API boundary")
    return _envelope(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        INTERNAL_ERROR_MESSAGE,
        INTERNAL_ERROR_CODE,
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register the global exception handlers on the FastAPI application.

    Specific domain errors keep their user-safe message and status; every other
    domain error and any unexpected exception map to a generic 500 envelope.
    """
    application.add_exception_handler(
        InappropriateContentError, _handle_inappropriate_content
    )
    application.add_exception_handler(RateLimitError, _handle_rate_limit)
    application.add_exception_handler(DomainError, _handle_domain_error)
    application.add_exception_handler(Exception, _handle_unexpected_error)
