"""Answer caching policy shared by the exact (Redis) and semantic (PostgreSQL) caches."""


def is_cacheable_answer(answer: str) -> bool:
    """Return ``False`` for empty or whitespace-only answers ('not found' responses)."""
    return bool(answer.strip())
