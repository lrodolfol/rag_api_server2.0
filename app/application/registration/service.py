"""Company registration ingestion service.

Orchestrates the full registration flow for a company/business:

* moderate the submitted content and stop when it is inappropriate;
* normalise and split the content into chunks;
* generate embeddings for each chunk;
* replace the client's vectors in the vector store (delete + upsert);
* persist the client record in object storage.

Normalisation and chunking are delegated to the text-processing helpers, and
every external interaction is delegated to the existing infrastructure services,
so this layer only coordinates the steps without duplicating their logic.
"""

from app.application.text_processing import generate_chunks
from app.domain import (
    CompanyData,
    CompanyRegistrationRequest,
    EmbeddingRecord,
    InappropriateContentError,
)
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai import OpenAIService
from app.infrastructure.pinecone import PineconeVectorRepository
from app.infrastructure.storage import ClientStorageRepository

logger = get_logger(__name__)


class RegistrationService:
    """Coordinate the ingestion pipeline for a company registration."""

    def __init__(
        self,
        openai_service: OpenAIService,
        vector_repository: PineconeVectorRepository,
        storage_repository: ClientStorageRepository,
    ) -> None:
        self._openai = openai_service
        self._vectors = vector_repository
        self._storage = storage_repository

    async def register(self, registration: CompanyRegistrationRequest) -> None:
        """Run the full ingestion flow for a single registration.

        Raises :class:`InappropriateContentError` (before anything is persisted)
        when moderation flags the submitted content.
        """
        logger.info("Starting company registration flow")
        company = registration.request
        content = self._build_content(company)
        await self._ensure_appropriate(content)
        embeddings = await self._build_embeddings(content)
        logger.info("Upserting %d embeddings to vector store", len(embeddings))
        await self._vectors.upsert_company_vectors(
            company.name, registration.user_code, embeddings
        )
        logger.info("Persisting client record to object storage")
        await self._storage.save_client(registration)
        logger.info("Company registration completed")

    async def _ensure_appropriate(self, content: str) -> None:
        """Moderate ``content`` and stop the flow when it is inappropriate."""
        logger.info("Submitting content to OpenAI moderation")
        result = await self._openai.moderate(content)
        if result.insult:
            logger.info("Registration rejected: inappropriate content detected")
            raise InappropriateContentError(
                "Submitted content was rejected by moderation"
            )
        logger.info("Content moderation passed")

    async def _build_embeddings(self, content: str) -> list[EmbeddingRecord]:
        """Normalise, chunk and embed ``content``."""
        chunks = generate_chunks(content)
        logger.info("Content split into %d chunks, generating embeddings", len(chunks))
        return await self._openai.generate_embeddings_from_chunks(chunks)

    @staticmethod
    def _build_content(company: CompanyData) -> str:
        """Compose a single text block from the company's fields."""
        fields = [
            company.name,
            company.descricao,
            company.address,
            company.telephone,
            company.email,
            company.detalhes,
        ]
        return "\n".join(fields)
