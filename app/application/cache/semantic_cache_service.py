"""Semantic answer cache service.

Hides the semantic cache record details (id, creation time, serialization) and
the database from the search flow. A lookup returns every match found by the
repository (most similar first); deciding which ones are close enough is up to
the caller (see ``SearchService.threshold_evaluate``).

Repository failures are already logged and turned into a miss (read) or ignored
(write), so this service never breaks the request.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.application.cache.answer_policy import is_cacheable_answer
from app.domain import CacheFingerprint, SemanticCacheEntry, SemanticCacheMatch
from app.infrastructure.postgres import PostgresSemanticCacheRepository


class SemanticCacheService:
    """Look up and store answers by question embedding similarity."""

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
        answer: str,
        embedding: list[float],
    ) -> None:
        """Persist the answer unless it is empty or the 'not found' fallback."""
        if not is_cacheable_answer(answer):
            return
        entry = SemanticCacheEntry(
            id=uuid4(),
            fingerprint=fingerprint,
            input_text=question,
            response=answer,
            embedding=embedding,
            # The column is a naive TIMESTAMP, so the value is stored as UTC.
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        await self._repository.save(entry)
