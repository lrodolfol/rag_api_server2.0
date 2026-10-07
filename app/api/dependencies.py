"""API dependency providers.

Build and cache the infrastructure clients and application services the routes
depend on, wiring them from the typed application configuration. Clients and
services are cached so they are constructed once per process instead of on every
request, and configuration is read lazily (on first use) rather than at import.
"""

from functools import lru_cache

from app.application.registration import RegistrationService
from app.infrastructure.config import AppConfig, get_config
from app.infrastructure.openai import OpenAIService, create_openai_client
from app.infrastructure.pinecone import (
    PineconeVectorRepository,
    create_pinecone_client,
)
from app.infrastructure.storage import ClientStorageRepository, create_s3_client


@lru_cache
def _openai_service() -> OpenAIService:
    config: AppConfig = get_config()
    client = create_openai_client(config.open_ai)
    return OpenAIService(client=client, config=config.open_ai)


@lru_cache
def _vector_repository() -> PineconeVectorRepository:
    config: AppConfig = get_config()
    client = create_pinecone_client(config.pinecone)
    return PineconeVectorRepository(client=client, config=config.pinecone)


@lru_cache
def _storage_repository() -> ClientStorageRepository:
    config: AppConfig = get_config()
    client = create_s3_client(config.bucket)
    return ClientStorageRepository(client=client, config=config.bucket)


def get_registration_service() -> RegistrationService:
    """Provide the registration service wired with its infrastructure deps."""
    return RegistrationService(
        openai_service=_openai_service(),
        vector_repository=_vector_repository(),
        storage_repository=_storage_repository(),
    )
