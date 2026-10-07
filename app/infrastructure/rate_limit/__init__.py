"""In-memory rate limiting package.

Exposes the per-IP online-chat rate limiter together with its limit/TTL
constants and the standardized block message returned when the limit is hit.
"""

from app.infrastructure.rate_limit.limiter import (
    MAX_MESSAGES_PER_WINDOW,
    RATE_LIMIT_MESSAGE,
    WINDOW_TTL_SECONDS,
    InMemoryRateLimiter,
)

__all__ = [
    "MAX_MESSAGES_PER_WINDOW",
    "RATE_LIMIT_MESSAGE",
    "WINDOW_TTL_SECONDS",
    "InMemoryRateLimiter",
]
