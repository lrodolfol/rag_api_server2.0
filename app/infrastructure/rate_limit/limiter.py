"""In-memory per-IP rate limiter for the online chat.

Limits each client IP to a fixed number of messages within a 5-hour window,
as required by the technical specification (§3.1). State is kept in process
memory only, so no external dependency is needed; a monotonic time source is
injected to keep expiry logic deterministic and unit-testable.

Reaching the limit raises the domain :class:`RateLimitError` carrying a
standardized, user-safe block message that the API layer wraps in the shared
response envelope.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Final

from app.domain import RateLimitError
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

MAX_MESSAGES_PER_WINDOW: Final[int] = 3
WINDOW_TTL_SECONDS: Final[int] = 5 * 60 * 60
RATE_LIMIT_MESSAGE: Final[str] = (
    "Você atingiu o limite de mensagens. Tente novamente mais tarde."
)


@dataclass
class _Window:
    """Message count for one IP and the monotonic time it expires."""

    count: int
    expires_at: float


class InMemoryRateLimiter:
    """Per-IP message rate limiter backed by an in-memory window map."""

    def __init__(
        self,
        max_messages: int = MAX_MESSAGES_PER_WINDOW,
        window_ttl_seconds: int = WINDOW_TTL_SECONDS,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_messages = max_messages
        self._window_ttl_seconds = window_ttl_seconds
        self._time_source = time_source
        self._windows: dict[str, _Window] = {}
        self._lock = asyncio.Lock()

    async def check_and_increment(self, ip: str) -> None:
        """Count a message for ``ip``, raising when the window limit is exceeded."""
        async with self._lock:
            now = self._time_source()
            window = self._active_window(ip, now)
            if window.count >= self._max_messages:
                logger.warning("Rate limit reached for an online chat client")
                raise RateLimitError(RATE_LIMIT_MESSAGE)
            window.count += 1
            self._windows[ip] = window

    def _active_window(self, ip: str, now: float) -> _Window:
        """Return the live window for ``ip`` or a fresh one when none/expired."""
        window = self._windows.get(ip)
        if window is None or window.expires_at <= now:
            return _Window(count=0, expires_at=now + self._window_ttl_seconds)
        return window
