"""API dependency providers.

Build and cache the infrastructure clients and application services the routes
depend on, wiring them from the typed application configuration. Clients and
services are cached so they are constructed once per process instead of on every
request, and configuration is read lazily (on first use) rather than at import.
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.application.cache import SemanticCacheService
from app.application.categories import CategoryService
from app.application.deletion import DeletionService
from app.application.registration import RegistrationService
from app.application.search import SearchService
from app.infrastructure.config import AppConfig, get_config
from app.infrastructure.openai import OpenAIService, create_openai_client
from app.infrastructure.pinecone import (
    PineconeVectorRepository,
    create_pinecone_client,
)
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import (
    RedisAnswerCacheRepository,
    RedisCategoryRepository,
    RedisHistoryRepository,
    create_redis_client,
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


@lru_cache
def _redis_client() -> Redis:
    # Shared by every Redis repository: one connection pool.
    config: AppConfig = get_config()
    return create_redis_client(config.redis)


@lru_cache
def _history_repository() -> RedisHistoryRepository:
    return RedisHistoryRepository(client=_redis_client())


@lru_cache
def _answer_cache_repository() -> RedisAnswerCacheRepository:
    return RedisAnswerCacheRepository(client=_redis_client())


@lru_cache
def _category_repository() -> RedisCategoryRepository:
    return RedisCategoryRepository(
        client=_redis_client(), config=get_config().categories
    )


@lru_cache
def _category_service() -> CategoryService:
    return CategoryService(
        repository=_category_repository(), config=get_config().categories
    )


@lru_cache
def _semantic_cache_repository() -> PostgresSemanticCacheRepository:
    config: AppConfig = get_config()
    return PostgresSemanticCacheRepository(
        postgres_config=config.postgres,
        semantic_cache_config=config.semantic_cache,
    )


@lru_cache
def _semantic_cache_service() -> SemanticCacheService:
    return SemanticCacheService(repository=_semantic_cache_repository())


@lru_cache
def _rate_limiter() -> InMemoryRateLimiter:
    # Cached so the in-memory per-IP windows are shared across all requests.
    return InMemoryRateLimiter()


def get_registration_service() -> RegistrationService:
    """Provide the registration service wired with its infrastructure deps."""
    return RegistrationService(
        openai_service=_openai_service(),
        vector_repository=_vector_repository(),
        storage_repository=_storage_repository(),
        category_service=_category_service(),
        semantic_cache=_semantic_cache_service(),
        answer_cache=_answer_cache_repository(),
    )


def get_deletion_service() -> DeletionService:
    """Provide the company deletion service wired with its infrastructure deps."""
    return DeletionService(
        vector_repository=_vector_repository(),
        storage_repository=_storage_repository(),
        semantic_cache=_semantic_cache_service(),
        answer_cache=_answer_cache_repository(),
    )


def get_search_service() -> SearchService:
    """Provide the shared RAG search service wired with its infrastructure deps."""
    return SearchService(
        openai_service=_openai_service(),
        vector_repository=_vector_repository(),
        history_repository=_history_repository(),
        answer_cache=_answer_cache_repository(),
        semantic_cache=_semantic_cache_service(),
        fingerprint_config=get_config().finger_print,
        category_service=_category_service(),
    )


def get_category_service() -> CategoryService:
    """Provide the knowledge-base categories service backed by the Redis catalog."""
    return _category_service()


def get_rate_limiter() -> InMemoryRateLimiter:
    """Provide the process-wide in-memory per-IP rate limiter."""
    return _rate_limiter()
