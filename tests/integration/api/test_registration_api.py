"""Integration tests for the company registration endpoint.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the
registration service is replaced with a fake via dependency override so no
external provider is contacted. The category test runs the real registration
service (catalog seeded by the app lifespan on an in-memory Redis) with fake
OpenAI, vector and storage boundaries.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.api.dependencies import get_category_service, get_registration_service
from app.application.cache import SemanticCacheService
from app.application.categories import CategoryService
from app.application.registration import RegistrationService
from app.domain import CompanyRegistrationRequest, EmbeddingRecord
from app.infrastructure.config import CategoriesConfig, PostgresConfig, SemanticCacheConfig
from app.infrastructure.openai import ModerationResult
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.redis import RedisAnswerCacheRepository, RedisCategoryRepository
from app.main import create_app

FOOD_KEY = "f" * 64
BEAUTY_KEY = "e" * 64
UNCATEGORIZED_KEY = "c" * 64


class _FakeRegistrationService:
    """In-memory stand-in recording registrations."""

    def __init__(self) -> None:
        self.calls: list[CompanyRegistrationRequest] = []

    async def register(self, registration: CompanyRegistrationRequest) -> None:
        self.calls.append(registration)


def _payload(user_code: str = "123", name: str = "Padaria") -> dict:
    return {
        "user_code": user_code,
        "request": {
            "name": name,
            "descricao": "bolos",
            "email": "shop@example.com",
            "address": "rua a",
            "telephone": "1199999",
            "detalhes": "detalhes",
        },
    }


def _semantic_cache() -> SemanticCacheService:
    postgres = PostgresConfig(
        host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
    )
    return SemanticCacheService(
        PostgresSemanticCacheRepository(postgres, SemanticCacheConfig(table="rag_response_cache", top_k=3))
    )


def _answer_cache(redis_client: Any = None) -> RedisAnswerCacheRepository:
    """Real exact-cache repository over an in-memory (or given) Redis client."""
    return RedisAnswerCacheRepository(redis_client or FakeAsyncRedis(decode_responses=True))


def _seeded_answer_cache() -> RedisAnswerCacheRepository:
    """Exact cache holding one answer in ``alimentacao``, one in ``beleza`` and one uncategorized."""
    answer_cache = _answer_cache()

    async def _seed() -> None:
        await answer_cache.set(FOOD_KEY, "Padaria", {"alimentacao"})
        await answer_cache.set(BEAUTY_KEY, "Salao", {"beleza"})
        await answer_cache.set(UNCATEGORIZED_KEY, "Padaria e Salao", {None})

    asyncio.run(_seed())
    return answer_cache


def _failing_redis() -> MagicMock:
    """Redis client whose every invalidation read fails, like an unreachable server."""
    client = MagicMock()
    client.smembers = AsyncMock(side_effect=RedisError("redis down"))
    return client


def _client(service: _FakeRegistrationService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    return TestClient(app)


def test_should_register_company_and_return_created_envelope() -> None:
    # Arrange
    service = _FakeRegistrationService()
    client = _client(service)

    # Act
    response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    body = response.json()
    assert body["status_code"] == 201
    assert body["errors"] == []
    assert len(service.calls) == 1
    assert service.calls[0].user_code == "123"


def test_should_reject_invalid_payload_with_validation_error() -> None:
    # Arrange
    service = _FakeRegistrationService()
    client = _client(service)

    # Act
    response = client.post("/companies", json={"user_code": "123"})

    # Assert
    assert response.status_code == 422
    assert service.calls == []


# --- Real registration service with a categorizing (fake) OpenAI ------------


class _CategorizingOpenAI:
    """Fake OpenAI returning a fixed category and recording the offered list."""

    def __init__(self, category: str) -> None:
        self._category = category
        self.offered_categories: list[list[str]] = []

    async def moderate(self, content: str, categories: list[str]) -> ModerationResult:
        self.offered_categories.append(categories)
        return ModerationResult(insult=False, insult_text="", category=self._category)

    async def generate_embeddings_from_chunks(
        self, chunks: list[str]
    ) -> list[EmbeddingRecord]:
        return [EmbeddingRecord(text=chunk, vector=[0.1, 0.2]) for chunk in chunks]


class _RecordingVectors:
    def __init__(self) -> None:
        self.upserted_slugs: list[str] = []

    async def get_category_by_user_code(self, user_code: str) -> str | None:
        return None

    async def upsert_company_vectors(
        self,
        company_name: str,
        user_code: str,
        category_slug: str,
        embeddings: list[EmbeddingRecord],
    ) -> None:
        self.upserted_slugs.append(category_slug)


class _RecordingStorage:
    def __init__(self) -> None:
        self.saved_slugs: list[str] = []

    async def save_client(
        self, registration: CompanyRegistrationRequest, category_slug: str
    ) -> None:
        self.saved_slugs.append(category_slug)

    async def delete_client(self, user_code: str, category_slug: str) -> None:
        raise AssertionError("first registration must not delete anything")


@pytest.mark.parametrize(
    ("llm_category", "expected_slug"),
    [("ALIMENTAÇÃO", "alimentacao"), ("Serviços Profissionais", "servicos_profissionais")],
)
def test_should_pass_category_slug_to_vectors_and_storage(
    llm_category: str, expected_slug: str, semantic_cache_db: Any
) -> None:
    # Arrange
    config = CategoriesConfig(
        redis_key="knowledge_categories",
        initial=["ALIMENTAÇÃO", "SERVIÇOS PROFISSIONAIS"],
        fallback="OUTROS",
    )
    redis_client = FakeAsyncRedis(decode_responses=True)
    categories = CategoryService(RedisCategoryRepository(redis_client, config), config)
    openai = _CategorizingOpenAI(llm_category)
    vectors = _RecordingVectors()
    storage = _RecordingStorage()
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
        category_service=categories,
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    app.dependency_overrides[get_category_service] = lambda: categories

    # Act
    with TestClient(app) as client:
        response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    assert openai.offered_categories == [["ALIMENTAÇÃO", "SERVIÇOS PROFISSIONAIS"]]
    assert vectors.upserted_slugs == [expected_slug]
    assert storage.saved_slugs == [expected_slug]


def _real_registration_client(
    openai: _CategorizingOpenAI,
    vectors: _RecordingVectors,
    answer_cache: RedisAnswerCacheRepository | None = None,
) -> TestClient:
    config = CategoriesConfig(
        redis_key="knowledge_categories", initial=["ALIMENTAÇÃO", "BELEZA"], fallback="OUTROS"
    )
    categories = CategoryService(RedisCategoryRepository(FakeAsyncRedis(decode_responses=True), config), config)
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=_RecordingStorage(),
        category_service=categories,
        semantic_cache=_semantic_cache(),
        answer_cache=answer_cache or _answer_cache(),
    )
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    app.dependency_overrides[get_category_service] = lambda: categories
    return TestClient(app)


def test_should_invalidate_registered_category_and_uncategorized_cache_rows(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    semantic_cache_db.rows = [{"category": slug} for slug in ("alimentacao", "beleza", None)]
    client = _real_registration_client(_CategorizingOpenAI("ALIMENTAÇÃO"), _RecordingVectors())

    # Act
    with client:
        response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza"]


def test_should_register_company_even_when_cache_invalidation_fails(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    semantic_cache_db.error = psycopg.OperationalError("db down")
    vectors = _RecordingVectors()
    client = _real_registration_client(_CategorizingOpenAI("ALIMENTAÇÃO"), vectors)

    # Act
    with client:
        response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    assert vectors.upserted_slugs == ["alimentacao"]


def test_should_invalidate_registered_category_and_uncategorized_exact_cache_answers(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    answer_cache = _seeded_answer_cache()
    client = _real_registration_client(
        _CategorizingOpenAI("ALIMENTAÇÃO"), _RecordingVectors(), answer_cache
    )

    # Act
    with client:
        response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    assert asyncio.run(answer_cache.get(FOOD_KEY)) is None
    assert asyncio.run(answer_cache.get(UNCATEGORIZED_KEY)) is None
    assert asyncio.run(answer_cache.get(BEAUTY_KEY)) == "Salao"


def test_should_register_company_even_when_redis_invalidation_fails(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    vectors = _RecordingVectors()
    client = _real_registration_client(
        _CategorizingOpenAI("ALIMENTAÇÃO"), vectors, _answer_cache(_failing_redis())
    )

    # Act
    with client:
        response = client.post("/companies", json=_payload())

    # Assert
    assert response.status_code == 201
    assert vectors.upserted_slugs == ["alimentacao"]
