"""Company deletion service.

Orchestrates the removal of a client's data:

* check whether the client has any vector in the vector store;
* when it has none, do nothing (the request still succeeds);
* otherwise read the client's category from its vectors (before deleting them,
  since the category only lives in their metadata), delete the vectors and then
  remove its record from the object storage file of that category;
* vectors stored before categories existed have no category: they are deleted,
  storage is left untouched and a warning is logged (the legacy record stays).

Every external interaction is delegated to the existing infrastructure
repositories; their domain errors propagate so the API layer can translate them
into a safe error response. ``user_code`` values are never logged.
"""

from app.domain import CompanyDeletionRequest
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.pinecone import PineconeVectorRepository
from app.infrastructure.storage import ClientStorageRepository

logger = get_logger(__name__)


class DeletionService:
    """Coordinate the deletion of a client's vectors and stored record."""

    def __init__(
        self,
        vector_repository: PineconeVectorRepository,
        storage_repository: ClientStorageRepository,
    ) -> None:
        self._vectors = vector_repository
        self._storage = storage_repository

    async def delete(self, request: CompanyDeletionRequest) -> None:
        """Delete the client's data when it has vectors; otherwise do nothing."""
        logger.info("Starting company deletion flow")
        user_code = request.user_code
        if not await self._vectors.has_vectors_for_user_code(user_code):
            logger.info("No vectors found for client; nothing to delete")
            return
        category_slug = await self._vectors.get_category_by_user_code(user_code)
        await self._vectors.delete_by_user_code(user_code)
        await self._delete_stored_record(user_code, category_slug)
        logger.info("Company deletion completed")

    async def _delete_stored_record(self, user_code: str, category_slug: str | None) -> None:
        """Remove the record from its category file; skip legacy uncategorized data."""
        if category_slug is None:
            logger.warning(
                "Client vectors had no category; legacy record was not removed from the bucket"
            )
            return
        logger.info("Removing client record from category '%s'", category_slug)
        await self._storage.delete_client(user_code, category_slug)
