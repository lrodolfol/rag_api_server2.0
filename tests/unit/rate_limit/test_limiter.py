"""Unit tests for :class:`InMemoryRateLimiter` (counting and expiration)."""

import pytest

from app.domain import RateLimitError
from app.infrastructure.rate_limit import (
    MAX_MESSAGES_PER_WINDOW,
    RATE_LIMIT_MESSAGE,
    InMemoryRateLimiter,
)


class _FakeClock:
    """Controllable monotonic clock for deterministic expiry tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _limiter(clock: _FakeClock, *, ttl: int = 100) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(
        max_messages=MAX_MESSAGES_PER_WINDOW,
        window_ttl_seconds=ttl,
        time_source=clock,
    )


@pytest.mark.asyncio
async def test_should_allow_up_to_the_configured_limit() -> None:
    # Arrange
    limiter = _limiter(_FakeClock())

    # Act / Assert
    for _ in range(MAX_MESSAGES_PER_WINDOW):
        await limiter.check_and_increment("200.148.12.188")


@pytest.mark.asyncio
async def test_should_block_when_limit_exceeded_with_standard_message() -> None:
    # Arrange
    limiter = _limiter(_FakeClock())
    ip = "200.148.12.188"
    for _ in range(MAX_MESSAGES_PER_WINDOW):
        await limiter.check_and_increment(ip)

    # Act / Assert
    with pytest.raises(RateLimitError) as exc_info:
        await limiter.check_and_increment(ip)
    assert str(exc_info.value) == RATE_LIMIT_MESSAGE


@pytest.mark.asyncio
async def test_should_track_each_ip_independently() -> None:
    # Arrange
    limiter = _limiter(_FakeClock())
    for _ in range(MAX_MESSAGES_PER_WINDOW):
        await limiter.check_and_increment("200.148.12.188")

    # Act / Assert: a different IP keeps its own fresh window.
    await limiter.check_and_increment("10.0.0.1")


@pytest.mark.asyncio
async def test_should_release_after_window_expires() -> None:
    # Arrange
    clock = _FakeClock()
    limiter = _limiter(clock, ttl=100)
    ip = "200.148.12.188"
    for _ in range(MAX_MESSAGES_PER_WINDOW):
        await limiter.check_and_increment(ip)

    # Act: move past the window TTL.
    clock.advance(101)

    # Assert: the IP is allowed again from a fresh window.
    await limiter.check_and_increment(ip)


@pytest.mark.asyncio
async def test_should_keep_blocking_within_the_same_window() -> None:
    # Arrange
    clock = _FakeClock()
    limiter = _limiter(clock, ttl=100)
    ip = "200.148.12.188"
    for _ in range(MAX_MESSAGES_PER_WINDOW):
        await limiter.check_and_increment(ip)

    # Act: time advances but stays inside the window.
    clock.advance(50)

    # Assert
    with pytest.raises(RateLimitError):
        await limiter.check_and_increment(ip)
