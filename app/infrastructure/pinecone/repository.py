"""Asynchronous Pinecone vector repository.

Provides the vector-store operations the RAG pipeline needs:

* create the index on demand (only when it does not already exist),
* replace a client's vectors on update (delete by ``user_code`` then upsert),
* check whether a client has any vector (metadata filter on ``user_code``),
* read a client's current category (``category`` metadata of its vectors),
* query by embedding (optionally filtered by category slug) and return only
  matches above the similarity threshold.

Index parameters always come from the typed :class:`PineconeConfig` (never
hardcoded). The Pinecone SDK is synchronous, so each blocking call is run in a
worker thread via :func:`asyncio.to_thread` to honour the application's async
contract without blocking the event loop. Every SDK failure is translated into
the domain :class:`VectorRepositoryError`; ``user_code`` values are never
logged.
"""

import asyncio
from typing import Any, Final

from pinecone import NotFoundException, Pinecone, ServerlessSpec
from pinecone.exceptions import PineconeException

from app.domain import EmbeddingRecord, VectorRepositoryError
from app.infrastructure.config import PineconeConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.pinecone.models import VectorMatch

logger = get_logger(__name__)

SIMILARITY_THRESHOLD: Final[float] = 0.41
DEFAULT_TOP_K: Final[int] = 5
CLOUD_PROVIDER: Final[str] = "aws"
VectorTuple = tuple[str, list[float], dict[str, str]]
MetadataFilter = dict[str, Any]


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
        category_slug: str,
        embeddings: list[EmbeddingRecord],
    ) -> None:
        """Replace a client's vectors: delete existing ones, then insert new.

        Deleting first keeps a client update idempotent instead of accumulating
        stale vectors across registrations. ``category_slug`` is stored in the
        ``category`` metadata of every vector.
        """
        if not embeddings:
            logger.info("No embeddings provided; skipping upsert")
            return
        await self.create_index_if_not_exists()
        vectors = self._build_vectors(company_name, user_code, category_slug, embeddings)
        await asyncio.to_thread(self._replace_vectors_sync, user_code, vectors)
        logger.info("Upserted %d vectors into index '%s'", len(vectors), self._config.index_name)

    async def has_vectors_for_user_code(self, user_code: str) -> bool:
        """Return whether at least one vector is stored for ``user_code``.

        Pinecone queries require a vector, so a neutral non-zero probe of the
        configured dimension is sent and only the metadata filter decides the
        result; the similarity threshold is deliberately not applied.
        """
        await self.create_index_if_not_exists()
        found = await asyncio.to_thread(self._has_vectors_sync, user_code)
        logger.info(
            "Vector existence check on index '%s' found vectors: %s",
            self._config.index_name,
            found,
        )
        return found

    async def get_category_by_user_code(self, user_code: str) -> str | None:
        """Return the category slug stored in the client's vectors.

        ``None`` when the client has no vectors or its vectors have no
        ``category`` metadata (data stored before categories existed).
        """
        await self.create_index_if_not_exists()
        category = await asyncio.to_thread(self._get_category_sync, user_code)
        logger.info(
            "Category lookup on index '%s' found category: '%s'",
            self._config.index_name,
            category,
        )
        return category

    async def delete_by_user_code(self, user_code: str) -> None:
        """Delete every vector whose metadata matches ``user_code``."""
        await self.create_index_if_not_exists()
        await asyncio.to_thread(self._delete_sync, user_code)
        logger.info("Deleted vectors from index '%s'", self._config.index_name)

    async def query(
        self,
        embedding: list[float],
        top_k: int = DEFAULT_TOP_K,
        category_slug: str | None = None,
    ) -> list[VectorMatch]:
        """Return matches for ``embedding`` with similarity above the threshold.

        With ``category_slug`` only vectors of that category are searched;
        without it the whole index is searched.
        """
        if not embedding:
            return []
        await self.create_index_if_not_exists()
        metadata_filter = self._category_filter(category_slug)
        logger.info(
            "Querying Pinecone index '%s' (top_k=%d, category_filter='%s')",
            self._config.index_name,
            top_k,
            category_slug if metadata_filter else "none",
        )
        response = await asyncio.to_thread(
            self._query_sync, embedding, top_k, metadata_filter
        )
        matches = self._filter_matches(response)
        logger.info("Pinecone query returned %d matches above threshold", len(matches))
        return matches

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

            try:
                index.delete(filter={"user_code": user_code})
            except NotFoundException:
                logger.warning(f"Namespace not found for delete user_code {user_code}. going ahead.")
            index.upsert(vectors=vectors)
        except PineconeException as error:
            logger.exception("Failed to upsert Pinecone vectors")
            raise VectorRepositoryError("Failed to store vectors") from error

    def _delete_sync(self, user_code: str) -> None:
        try:
            index = self._client.Index(self._config.index_name)
            index.delete(filter={"user_code": user_code})
        except NotFoundException:
            logger.warning("No vectors found to delete in index '%s'", self._config.index_name)
        except PineconeException as error:
            logger.exception("Failed to delete Pinecone vectors")
            raise VectorRepositoryError("Failed to delete vectors") from error

    def _has_vectors_sync(self, user_code: str) -> bool:
        try:
            response = self._probe_user_code(user_code, include_metadata=False)
        except NotFoundException:
            return False
        except PineconeException as error:
            logger.exception("Failed to check Pinecone vectors")
            raise VectorRepositoryError("Failed to check vectors") from error
        return bool(getattr(response, "matches", None))

    def _get_category_sync(self, user_code: str) -> str | None:
        try:
            response = self._probe_user_code(user_code, include_metadata=True)
        except NotFoundException:
            return None
        except PineconeException as error:
            logger.exception("Failed to read the client category from Pinecone")
            raise VectorRepositoryError("Failed to read vector category") from error
        matches = getattr(response, "matches", None) or []
        if not matches:
            return None
        metadata = getattr(matches[0], "metadata", None) or {}
        category = metadata.get("category")
        return str(category) if category else None

    def _probe_user_code(self, user_code: str, include_metadata: bool) -> object:
        """Query the client's first vector with a neutral non-zero probe.

        Pinecone queries require a vector (cosine indexes reject a zero one), so
        only the ``user_code`` metadata filter decides the result.
        """
        probe = [1.0] * self._config.dimension
        index = self._client.Index(self._config.index_name)
        return index.query(
            vector=probe,
            top_k=1,
            filter={"user_code": user_code},
            include_metadata=include_metadata,
        )

    def _query_sync(
        self,
        embedding: list[float],
        top_k: int,
        metadata_filter: MetadataFilter | None,
    ) -> object:
        options = {"filter": metadata_filter} if metadata_filter else {}
        try:
            index = self._client.Index(self._config.index_name)
            return index.query(
                vector=embedding, top_k=top_k, include_metadata=True, **options
            )
        except PineconeException as error:
            logger.exception("Failed to query Pinecone")
            raise VectorRepositoryError("Failed to query vectors") from error

    @staticmethod
    def _category_filter(category_slug: str | None) -> MetadataFilter | None:
        if not category_slug:
            return None
        return {"category": {"$eq": category_slug}}

    @staticmethod
    def _build_vectors(
        company_name: str,
        user_code: str,
        category_slug: str,
        embeddings: list[EmbeddingRecord],
    ) -> list[VectorTuple]:
        prefix = company_name.replace(" ", "")
        return [
            (
                f"{prefix}-{user_code}-{index}",
                record.vector,
                {"text": record.text, "user_code": user_code, "category": category_slug},
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
                    category=str(metadata.get("category", "")),
                )
            )
        return results
