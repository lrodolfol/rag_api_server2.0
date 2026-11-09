"""Integration tests for the company registration endpoint.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the
registration service is replaced with a fake via dependency override so no
external provider is contacted. The category test runs the real registration
service (catalog seeded by the app lifespan on an in-memory Redis) with fake
OpenAI, vector and storage boundaries.
"""

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api.dependencies import get_category_service, get_registration_service
from app.application.categories import CategoryService
from app.application.registration import RegistrationService
from app.domain import CompanyRegistrationRequest, EmbeddingRecord
from app.infrastructure.config import CategoriesConfig
from app.infrastructure.openai import ModerationResult
from app.infrastructure.redis import RedisCategoryRepository
from app.main import create_app


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
    llm_category: str, expected_slug: str
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
