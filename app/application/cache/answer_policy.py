"""Answer caching policy shared by the exact (Redis) and semantic (PostgreSQL) caches."""

from app.domain import ChatAnswer


def is_cacheable_answer(answer: ChatAnswer) -> bool:
    """Return ``False`` for answers without items ('not found' responses)."""
    return not answer.is_empty()
