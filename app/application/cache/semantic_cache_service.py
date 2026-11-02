"""Semantic answer cache service.

Hides the semantic cache record details (id, creation time, serialization) and
the database from the search flow. A lookup is a hit whenever the repository
returns at least one match: the closest one (``best_match``) is used and no
minimum similarity threshold is applied in this version.

Repository failures are already logged and turned into a miss (read) or ignored
(write), so this service never breaks the request.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.application.cache.answer_policy import is_cacheable_answer
from app.domain import CacheFingerprint, SemanticCacheEntry
from app.infrastructure.postgres import PostgresSemanticCacheRepository


class SemanticCacheService:
    """Look up and store answers by question embedding similarity."""

    def __init__(self, repository: PostgresSemanticCacheRepository) -> None:
        self._repository = repository

    async def find_answer(
        self, fingerprint: CacheFingerprint, embedding: list[float]
    ) -> str | None:
        """Return the closest cached answer for the fingerprint, or ``None`` on miss."""
        matches = await self._repository.find_nearest(embedding, fingerprint)
        if not matches:
            return None
        best_match = matches[0]
        return best_match.response

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
