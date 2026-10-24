"""Company deletion service.

Orchestrates the removal of a client's data:

* check whether the client has any vector in the vector store;
* when it has none, do nothing (the request still succeeds);
* otherwise delete its vectors and then its record in object storage.

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
        if not await self._vectors.has_vectors_for_user_code(request.user_code):
            logger.info("No vectors found for client; nothing to delete")
            return
        await self._vectors.delete_by_user_code(request.user_code)
        await self._storage.delete_client(request.user_code)
        logger.info("Company deletion completed")
