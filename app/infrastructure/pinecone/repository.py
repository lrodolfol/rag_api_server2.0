"""Asynchronous Pinecone vector repository.

Provides the vector-store operations the RAG pipeline needs:

* create the index on demand (only when it does not already exist),
* replace a client's vectors on update (delete by ``user_code`` then upsert),
* query by embedding and return only matches above the similarity threshold.

Index parameters always come from the typed :class:`PineconeConfig` (never
hardcoded). The Pinecone SDK is synchronous, so each blocking call is run in a
worker thread via :func:`asyncio.to_thread` to honour the application's async
contract without blocking the event loop. Every SDK failure is translated into
the domain :class:`VectorRepositoryError`; ``user_code`` values are never
logged.
"""

import asyncio
from typing import Final

from pinecone import Pinecone, ServerlessSpec
from pinecone.exceptions import PineconeException

from app.domain import EmbeddingRecord, VectorRepositoryError
from app.infrastructure.config import PineconeConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.pinecone.models import VectorMatch

logger = get_logger(__name__)

SIMILARITY_THRESHOLD: Final[float] = 0.9
DEFAULT_TOP_K: Final[int] = 5
CLOUD_PROVIDER: Final[str] = "aws"
VectorTuple = tuple[str, list[float], dict[str, str]]


class PineconeVectorRepository:
    """Async repository over a Pinecone serverless index."""

    def __init__(self, client: Pinecone, config: PineconeConfig) -> None:
        self._client = client
        self._config = config

    async def create_index_if_not_exists(self) -> None:
        """Create the configured index when it is not already present."""
        await asyncio.to_thread(self._create_index_if_not_exists_sync)

    async def upsert_company_vectors(
        self,
        company_name: str,
        user_code: str,
        embeddings: list[EmbeddingRecord],
    ) -> None:
        """Replace a client's vectors: delete existing ones, then insert new.

        Deleting first keeps a client update idempotent instead of accumulating
        stale vectors across registrations.
        """
        if not embeddings:
            logger.info("No embeddings provided; skipping upsert")
            return
        await self.create_index_if_not_exists()
        vectors = self._build_vectors(company_name, user_code, embeddings)
        await asyncio.to_thread(self._replace_vectors_sync, user_code, vectors)
        logger.info("Upserted %d vectors into index '%s'", len(vectors), self._config.index_name)

    async def delete_by_user_code(self, user_code: str) -> None:
        """Delete every vector whose metadata matches ``user_code``."""
        await self.create_index_if_not_exists()
        await asyncio.to_thread(self._delete_sync, user_code)
        logger.info("Deleted vectors from index '%s'", self._config.index_name)

    async def query(
        self, embedding: list[float], top_k: int = DEFAULT_TOP_K
    ) -> list[VectorMatch]:
        """Return matches for ``embedding`` with similarity above the threshold."""
        if not embedding:
            return []
        await self.create_index_if_not_exists()
        response = await asyncio.to_thread(self._query_sync, embedding, top_k)
        return self._filter_matches(response)

    def _create_index_if_not_exists_sync(self) -> None:
        try:
            if self._client.has_index(self._config.index_name):
                return
            self._client.create_index(
                name=self._config.index_name,
                dimension=self._config.dimension,
                metric=self._config.metric,
                vector_type=self._config.vector_type,
                spec=ServerlessSpec(cloud=CLOUD_PROVIDER, region=self._config.region),
                deletion_protection="disabled",
                tags={"environment": self._config.environment},
            )
            logger.info("Pinecone index '%s' created", self._config.index_name)
        except PineconeException as error:
            logger.exception("Failed to create Pinecone index")
            raise VectorRepositoryError("Failed to create vector index") from error

    def _replace_vectors_sync(self, user_code: str, vectors: list[VectorTuple]) -> None:
        try:
            index = self._client.Index(self._config.index_name)
            index.delete(filter={"user_code": user_code})
            index.upsert(vectors=vectors)
        except PineconeException as error:
            logger.exception("Failed to upsert Pinecone vectors")
            raise VectorRepositoryError("Failed to store vectors") from error

    def _delete_sync(self, user_code: str) -> None:
        try:
            index = self._client.Index(self._config.index_name)
            index.delete(filter={"user_code": user_code})
        except PineconeException as error:
            logger.exception("Failed to delete Pinecone vectors")
            raise VectorRepositoryError("Failed to delete vectors") from error

    def _query_sync(self, embedding: list[float], top_k: int) -> object:
        try:
            index = self._client.Index(self._config.index_name)
            return index.query(vector=embedding, top_k=top_k, include_metadata=True)
        except PineconeException as error:
            logger.exception("Failed to query Pinecone")
            raise VectorRepositoryError("Failed to query vectors") from error

    @staticmethod
    def _build_vectors(
        company_name: str, user_code: str, embeddings: list[EmbeddingRecord]
    ) -> list[VectorTuple]:
        prefix = company_name.replace(" ", "")
        return [
            (
                f"{prefix}-{user_code}-{index}",
                record.vector,
                {"text": record.text, "user_code": user_code},
            )
            for index, record in enumerate(embeddings)
        ]

    @staticmethod
    def _filter_matches(response: object) -> list[VectorMatch]:
        matches = getattr(response, "matches", None) or []
        results: list[VectorMatch] = []
        for match in matches:
            score = getattr(match, "score", None)
            if score is None or score <= SIMILARITY_THRESHOLD:
                continue
            metadata = getattr(match, "metadata", None) or {}
            results.append(
                VectorMatch(
                    id=str(getattr(match, "id", "")),
                    score=float(score),
                    text=str(metadata.get("text", "")),
                    user_code=str(metadata.get("user_code", "")),
                )
            )
        return results
