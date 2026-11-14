"""Semantic answer cache service.

Hides the semantic cache record details (id, creation time, serialization) and
the database from the search, registration and deletion flows. A lookup returns
every match found by the repository (most similar first); deciding which ones
are close enough is up to the caller (see ``SearchService.threshold_evaluate``).

Every stored answer is tagged with the slug of the category the question was
classified into (``None`` when the search ran without a category filter).
Invalidating a category drops its answers together with the uncategorized
ones, since those may hold services of any category; invalidating ``None``
drops only the uncategorized answers.

Repository failures are already logged and turned into a miss (read) or ignored
(write), so this service never breaks the request.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.application.cache.answer_policy import is_cacheable_answer
from app.domain import CacheFingerprint, ChatAnswer, SemanticCacheEntry, SemanticCacheMatch
from app.infrastructure.postgres import PostgresSemanticCacheRepository


class SemanticCacheService:
    """Look up, store and invalidate (by category) semantically cached answers."""

    def __init__(self, repository: PostgresSemanticCacheRepository) -> None:
        self._repository = repository

    async def find_answer(
        self, fingerprint: CacheFingerprint, embedding: list[float]
    ) -> list[SemanticCacheMatch]:
        """Return every cached match for the fingerprint, most similar first (``[]`` on miss)."""
        return await self._repository.find_nearest(embedding, fingerprint)

    async def store(
        self,
        fingerprint: CacheFingerprint,
        question: str,
        answer: ChatAnswer,
        embedding: list[float],
        category_slug: str | None,
    ) -> None:
        """Persist the answer JSON, tagged with the question's category, unless it has no items."""
        if not is_cacheable_answer(answer):
            return
        entry = SemanticCacheEntry(
            id=uuid4(),
            fingerprint=fingerprint,
            input_text=question,
            response=answer.to_json(),
            embedding=embedding,
            # The column is a naive TIMESTAMP, so the value is stored as UTC.
            created_at=datetime.now(UTC).replace(tzinfo=None),
            category=category_slug,
        )
        await self._repository.save(entry)

    async def invalidate_category(self, category_slug: str | None) -> None:
        """Drop the answers of ``category_slug`` and the uncategorized ones.

        With ``None`` only the uncategorized answers are dropped. A blank slug
        is a caller bug (it would silently behave like ``None``) and raises
        ``ValueError``. Database failures are logged by the repository and
        never raised.
        """
        if category_slug is not None and not category_slug.strip():
            raise ValueError("Category slug must not be blank")
        await self._repository.delete_by_category(category_slug)
