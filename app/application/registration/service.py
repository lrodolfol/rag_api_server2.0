"""Company registration ingestion service.

Orchestrates the full registration flow for a company/business:

* read the category names from the catalog (Redis);
* moderate and classify the submitted content in a single LLM call, stopping
  when it is inappropriate (before anything is persisted);
* resolve the category (existing, new or the configured fallback), adding a new
  one to the catalog;
* read the client's previous category from its vectors (before the upsert,
  which deletes them);
* normalise, chunk and embed the content and replace the client's vectors
  (delete + upsert) tagged with the category slug;
* invalidate the semantic and exact (Redis) cache answers of the new category
  (and of the previous one when the client moved), right after the upsert;
* when the category changed, remove the client's record from the previous
  category object in storage;
* persist the client record in the object of its category.

Normalisation and chunking are delegated to the text-processing helpers, and
every external interaction is delegated to the existing infrastructure services,
so this layer only coordinates the steps without duplicating their logic.
``user_code`` values and client content are never logged.
"""

from app.application.cache import SemanticCacheService
from app.application.categories import CategoryService
from app.application.text_processing import generate_chunks
from app.domain import (
    Category,
    CompanyData,
    CompanyRegistrationRequest,
    EmbeddingRecord,
    InappropriateContentError,
)
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.openai import OpenAIService
from app.infrastructure.pinecone import PineconeVectorRepository
from app.infrastructure.redis import RedisAnswerCacheRepository
from app.infrastructure.storage import ClientStorageRepository

logger = get_logger(__name__)


class RegistrationService:
    """Coordinate the ingestion pipeline for a company registration."""

    def __init__(
        self,
        openai_service: OpenAIService,
        vector_repository: PineconeVectorRepository,
        storage_repository: ClientStorageRepository,
        category_service: CategoryService,
        semantic_cache: SemanticCacheService,
        answer_cache: RedisAnswerCacheRepository,
    ) -> None:
        self._openai = openai_service
        self._vectors = vector_repository
        self._storage = storage_repository
        self._categories = category_service
        self._semantic_cache = semantic_cache
        self._answer_cache = answer_cache

    async def register(self, registration: CompanyRegistrationRequest) -> None:
        """Run the full ingestion flow for a single registration.

        Raises :class:`InappropriateContentError` (before anything is persisted)
        when moderation flags the submitted content.
        """
        logger.info("Starting company registration flow")
        company = registration.request
        user_code = registration.user_code
        content = self._build_content(company)
        category = await self._moderate_and_classify(content)
        previous_slug = await self._vectors.get_category_by_user_code(user_code)
        embeddings = await self._build_embeddings(content)
        logger.info("Upserting %d embeddings to vector store", len(embeddings))
        await self._vectors.upsert_company_vectors(
            company.name, user_code, category.slug, embeddings
        )
        await self._invalidate_caches(previous_slug, category.slug)
        await self._remove_from_previous_category(user_code, previous_slug, category.slug)
        logger.info("Persisting client record to object storage")
        await self._storage.save_client(registration, category.slug)
        logger.info("Company registration completed (category='%s')", category.slug)

    async def _moderate_and_classify(self, content: str) -> Category:
        """Moderate ``content``, stop when inappropriate, and resolve its category."""
        categories = await self._categories.list_names()
        logger.info("Submitting content to OpenAI moderation and classification")
        result = await self._openai.moderate(content, categories)
        if result.insult:
            logger.info("Registration rejected: inappropriate content detected")
            raise InappropriateContentError(
                "Submitted content was rejected by moderation"
            )
        logger.info("Content moderation passed")
        category = await self._categories.resolve_or_create(result.category)
        logger.info("Registration category defined: '%s'", category.name)
        return category

    async def _invalidate_caches(self, previous_slug: str | None, new_slug: str) -> None:
        """Drop the cached answers of the new category and, if it changed, the old one."""
        await self._invalidate_category(new_slug)
        if previous_slug is not None and previous_slug != new_slug:
            await self._invalidate_category(previous_slug)

    async def _invalidate_category(self, category_slug: str) -> None:
        """Drop the answers of ``category_slug`` from the semantic and exact caches."""
        await self._semantic_cache.invalidate_category(category_slug)
        await self._answer_cache.invalidate_category(category_slug)

    async def _remove_from_previous_category(
        self, user_code: str, previous_slug: str | None, new_slug: str
    ) -> None:
        """Delete the client's record from the old category object when it changed."""
        if previous_slug is None or previous_slug == new_slug:
            logger.info("Client category unchanged (category='%s')", new_slug)
            return
        logger.info("Client category changed from '%s' to '%s'", previous_slug, new_slug)
        await self._storage.delete_client(user_code, previous_slug)

    async def _build_embeddings(self, content: str) -> list[EmbeddingRecord]:
        """Normalise, chunk and embed ``content``."""
        chunks = generate_chunks(content)
        logger.info("Content split into %d chunks, generating embeddings", len(chunks))
        return await self._openai.generate_embeddings_from_chunks(chunks)

    @staticmethod
    def _build_content(company: CompanyData) -> str:
        """Compose a single text block from the company's fields."""
        fields = [
            f"Name: {company.name}",
            f"Description: {company.descricao}",
            f"Address: {company.address}",
            f"Telephone: {company.telephone}",
            f"Email: {company.email}",
            f"Details: {company.detalhes}",
        ]
        return "\n".join(fields)
