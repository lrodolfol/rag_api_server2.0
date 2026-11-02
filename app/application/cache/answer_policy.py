"""Answer caching policy shared by the exact (Redis) and semantic (PostgreSQL) caches."""

from app.domain import PATTERN_RESPONSE


def is_cacheable_answer(answer: str) -> bool:
    """Return ``False`` for empty answers and the 'not found' fallback answer."""
    stripped_answer = answer.strip()
    return bool(stripped_answer) and stripped_answer != PATTERN_RESPONSE.strip()
