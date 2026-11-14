"""End-to-end integration tests for the three application flows.

Unlike the per-endpoint API tests (which replace the whole application service),
these exercise the *real* :class:`RegistrationService` and :class:`SearchService`
orchestration through the real routes, global exception handlers and response
envelope. Only the external dependencies (OpenAI, Pinecone, Redis, S3 and the
PostgreSQL semantic cache via the ``semantic_cache_db`` fixture) are replaced
with in-memory fakes, so the full application wiring is covered while no
external provider is contacted. Search answers arrive as Server-Sent Events
streams and are decoded event by event, with the delay between events removed.
"""

import asyncio
import json
from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from httpx import Response

from app.api.dependencies import (
    get_deletion_service,
    get_rate_limiter,
    get_registration_service,
    get_search_service,
)
from app.api.patterns import streaming
from app.application.cache import SemanticCacheService
from app.application.categories import CategoryService
from app.application.deletion import DeletionService
from app.application.registration import RegistrationService
from app.application.search import SearchService
from app.application.search import service as search_service
from app.domain import (
    ChatAnswer,
    CompanyRegistrationRequest,
    EmbeddingRecord,
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
    VectorRepositoryError,
)
from app.infrastructure.config import (
    CategoriesConfig,
    FingerPrintConfig,
    PostgresConfig,
    SemanticCacheConfig,
)
from app.infrastructure.openai.models import ModerationResult
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import (
    ANSWER_CACHE_CATEGORY_PREFIX,
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    UNCATEGORIZED_SLUG,
    HistoryChannel,
    RedisAnswerCacheRepository,
    RedisCategoryRepository,
)
from app.main import create_app


INTRO = "Encontrei para você:"
NOT_FOUND = "Nada encontrado."
CATEGORIES_CONFIG = CategoriesConfig(
    redis_key="knowledge_categories", initial=["ALIMENTAÇÃO", "BELEZA"], fallback="OUTROS"
)


def _category_service() -> CategoryService:
    """Category service over an in-memory Redis already holding the initial list."""
    client = FakeAsyncRedis(decode_responses=True)
    repository = RedisCategoryRepository(client, CATEGORIES_CONFIG)
    return CategoryService(repository=repository, config=CATEGORIES_CONFIG)


@pytest.fixture(autouse=True)
def _fixed_search_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the random intro and not-found messages with a single fixed one."""
    monkeypatch.setattr(search_service, "_ANSWER_MESSAGES", (INTRO,))
    monkeypatch.setattr(search_service, "_NOT_FOUND_MESSAGES", (NOT_FOUND,))


@pytest.fixture(autouse=True)
def _no_stream_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the pause between SSE events so the tests never wait."""
    monkeypatch.setattr(streaming, "STREAM_DELAY_SECONDS", 0)


def _sse_messages(response: Response) -> list[str]:
    """Assert a successful SSE answer and decode the message of each event."""
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [event for event in response.text.split("\n\n") if event]
    assert all(event.startswith("data: ") for event in events)
    return [json.loads(event.removeprefix("data: "))["message"] for event in events]


class _FakeOpenAIService:
    """In-memory stand-in for the OpenAI provider boundary."""

    def __init__(
        self,
        *,
        insult: bool = False,
        answer: str = "Padaria Central",
        category: str = "ALIMENTAÇÃO",
    ) -> None:
        self._insult = insult
        self._answer = answer
        self.category = category
        self.chat_phrases: list[list[str]] = []
        self.embedded_questions: list[str] = []

    async def moderate(self, content: str, categories: list[str]) -> ModerationResult:
        return ModerationResult(
            insult=self._insult,
            insult_text=content if self._insult else "",
            category=self.category,
        )

    async def classify_question(self, question: str, categories: list[str]) -> str:
        return self.category

    async def generate_embeddings_from_chunks(
        self, chunks: list[str]
    ) -> list[EmbeddingRecord]:
        return [EmbeddingRecord(text=chunk, vector=[0.1, 0.2, 0.3]) for chunk in chunks]

    async def generate_embedding_for_question(self, question: str) -> list[float]:
        self.embedded_questions.append(question)
        return [0.1, 0.2, 0.3]

    async def generate_chat_answer(
        self, payload: PayloadQuestionOpenIA, phrases: list[str]
    ) -> ChatAnswer:
        self.chat_phrases.append(phrases)
        return ChatAnswer(respostas=[self._answer])


class _FakeVectorRepository:
    """In-memory stand-in for the Pinecone vector store."""

    def __init__(
        self, matches: list[VectorMatch] | None = None, *, fail_query: bool = False
    ) -> None:
        self._matches = matches or []
        self._fail_query = fail_query
        self.upserts: list[tuple[str, str, list[EmbeddingRecord], str]] = []
        self.queried_categories: list[str | None] = []

    async def upsert_company_vectors(
        self,
        company_name: str,
        user_code: str,
        category_slug: str,
        embeddings: list[EmbeddingRecord],
    ) -> None:
        self.upserts = [upsert for upsert in self.upserts if upsert[1] != user_code]
        self.upserts.append((company_name, user_code, embeddings, category_slug))

    async def query(
        self, embedding: list[float], top_k: int = 5, category_slug: str | None = None
    ) -> list[VectorMatch]:
        if self._fail_query:
            raise VectorRepositoryError("Failed to query vectors")
        self.queried_categories.append(category_slug)
        # Fixed matches plus the registered chunks of the requested category.
        registered = [
            VectorMatch(id=company, score=0.95, text=record.text, user_code=code, category=slug)
            for company, code, records, slug in self.upserts
            for record in records
            if category_slug in (None, slug)
        ]
        return [*self._matches, *registered]

    async def get_category_by_user_code(self, user_code: str) -> str | None:
        return next((upsert[3] for upsert in self.upserts if upsert[1] == user_code), None)

    async def has_vectors_for_user_code(self, user_code: str) -> bool:
        return any(upsert[1] == user_code for upsert in self.upserts)

    async def delete_by_user_code(self, user_code: str) -> None:
        self.upserts = [upsert for upsert in self.upserts if upsert[1] != user_code]


class _FakeStorageRepository:
    """In-memory stand-in for the S3 client-record store."""

    def __init__(self) -> None:
        self.objects: dict[str, list[CompanyRegistrationRequest]] = {}

    @property
    def saved(self) -> list[CompanyRegistrationRequest]:
        return [item for records in self.objects.values() for item in records]

    async def save_client(
        self, registration: CompanyRegistrationRequest, category_slug: str
    ) -> None:
        await self.delete_client(registration.user_code, category_slug)
        self.objects.setdefault(category_slug, []).append(registration)

    async def delete_client(self, user_code: str, category_slug: str) -> None:
        records = self.objects.get(category_slug, [])
        self.objects[category_slug] = [item for item in records if item.user_code != user_code]


class _FakeHistoryRepository:
    """In-memory stand-in for the Redis conversation-history store."""

    def __init__(self, history: list[MessageHistoryItem] | None = None) -> None:
        self._initial = history or []
        self.appended: list[tuple[HistoryChannel, str, MessageHistoryItem]] = []

    async def get_history(
        self, channel: HistoryChannel, user_code: str
    ) -> list[MessageHistoryItem]:
        return list(self._initial)

    async def append_message(
        self, channel: HistoryChannel, user_code: str, message: MessageHistoryItem
    ) -> None:
        self.appended.append((channel, user_code, message))


FINGER_PRINT = FingerPrintConfig(
    prompt_version="1.0.0", rules_version="1.0.0", model_capability="economic"
)
POSTGRES_CONFIG = PostgresConfig(
    host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
)
SEMANTIC_CACHE_CONFIG = SemanticCacheConfig(table="rag_response_cache", top_k=3)


def _semantic_cache() -> SemanticCacheService:
    """Real semantic cache service over the in-memory ``semantic_cache_db`` fixture."""
    return SemanticCacheService(
        PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)
    )


def _answer_cache(redis_client: FakeAsyncRedis | None = None) -> RedisAnswerCacheRepository:
    """Real exact-cache repository over an in-memory (or the given) Redis client."""
    return RedisAnswerCacheRepository(redis_client or FakeAsyncRedis(decode_responses=True))


def _search_service(
    openai: _FakeOpenAIService,
    vectors: _FakeVectorRepository,
    history: _FakeHistoryRepository,
    redis_client: FakeAsyncRedis | None = None,
    category_service: CategoryService | None = None,
) -> SearchService:
    """Build the real search service with real caches on fake Redis/PostgreSQL.

    Callers must request the ``semantic_cache_db`` fixture so the semantic cache
    repository talks to the in-memory database.
    """
    client = redis_client or FakeAsyncRedis(decode_responses=True)
    return SearchService(
        openai_service=openai,
        vector_repository=vectors,
        history_repository=history,
        answer_cache=RedisAnswerCacheRepository(client),
        semantic_cache=_semantic_cache(),
        fingerprint_config=FINGER_PRINT,
        category_service=category_service or _category_service(),
    )


def _registration_payload(user_code: str = "123", name: str = "Padaria") -> dict:
    return {
        "user_code": user_code,
        "request": {
            "name": name,
            "descricao": "bolos e paes",
            "email": "shop@example.com",
            "address": "rua a",
            "telephone": "1199999",
            "detalhes": "aberto de seg a sex",
        },
    }


# --- Registration flow -------------------------------------------------------


def test_e2e_should_register_company_through_real_service(semantic_cache_db: Any) -> None:
    # Arrange: real RegistrationService wired to fake external deps.
    openai = _FakeOpenAIService()
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
        category_service=_category_service(),
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    client = TestClient(app)

    # Act
    response = client.post("/companies", json=_registration_payload())

    # Assert: HTTP envelope plus evidence the whole pipeline ran.
    assert response.status_code == 201
    assert response.json()["status_code"] == 201
    assert len(vectors.upserts) == 1
    assert vectors.upserts[0][1] == "123"
    assert vectors.upserts[0][3] == "alimentacao"
    assert [item.user_code for item in storage.objects["alimentacao"]] == ["123"]


def test_e2e_should_move_client_to_new_category_on_registration_update(semantic_cache_db: Any) -> None:
    # Arrange: the client first registers a restaurant, then a beauty salon.
    openai = _FakeOpenAIService(category="ALIMENTAÇÃO")
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    categories = _category_service()
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
    client = TestClient(app)
    client.post("/companies", json=_registration_payload("123"))
    semantic_cache_db.rows = [{"category": slug} for slug in ("alimentacao", "pet_shop", "beleza", None)]
    openai.category = "Pet Shop"

    # Act
    response = client.post("/companies", json=_registration_payload("123", "Pet Feliz"))

    # Assert: vectors and record moved to the new category, added to the catalog.
    assert response.status_code == 201
    assert [(upsert[1], upsert[3]) for upsert in vectors.upserts] == [("123", "pet_shop")]
    assert storage.objects["alimentacao"] == []
    assert [item.user_code for item in storage.objects["pet_shop"]] == ["123"]
    assert "PET SHOP" in asyncio.run(categories.list_names())
    # Both the old and the new category were invalidated (plus the uncategorized rows).
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza"]


def test_e2e_should_reject_inappropriate_registration_without_persisting(semantic_cache_db: Any) -> None:
    # Arrange: moderation flags the content as inappropriate.
    openai = _FakeOpenAIService(insult=True)
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    service = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
        category_service=_category_service(),
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: service
    client = TestClient(app)

    # Act
    response = client.post("/companies", json=_registration_payload())

    # Assert: rejected before anything is persisted.
    assert response.status_code == 400
    assert "inappropriate_content" in response.json()["errors"]
    assert vectors.upserts == []
    assert storage.saved == []


# --- Deletion flow -----------------------------------------------------------


def test_e2e_should_register_then_delete_company_through_real_services(semantic_cache_db: Any) -> None:
    # Arrange: real registration and deletion services sharing fake external deps.
    openai = _FakeOpenAIService(category="ALIMENTAÇÃO")
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    registration = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=storage,
        category_service=_category_service(),
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    deletion = DeletionService(
        vector_repository=vectors,
        storage_repository=storage,
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: registration
    app.dependency_overrides[get_deletion_service] = lambda: deletion
    client = TestClient(app)
    client.post("/companies", json=_registration_payload("123"))
    openai.category = "BELEZA"
    client.post("/companies", json=_registration_payload("456", "Salao"))

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert: only the target client's vectors and category record were removed.
    assert response.status_code == 200
    assert response.json()["status_code"] == 200
    assert [upsert[1] for upsert in vectors.upserts] == ["456"]
    assert storage.objects["alimentacao"] == []
    assert [item.user_code for item in storage.objects["beleza"]] == ["456"]


# --- WhatsApp search flow ----------------------------------------------------


def test_e2e_should_answer_whatsapp_message_through_real_service(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Padaria Central")
    matches = [VectorMatch(id="v1", score=0.95, text="Padaria Central", user_code="1")]
    vectors = _FakeVectorRepository(matches=matches)
    history = _FakeHistoryRepository()
    service = _search_service(openai, vectors, history)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    client = TestClient(app)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert: answer returned and the turn was persisted on the WhatsApp channel.
    assert _sse_messages(response) == [INTRO, "Padaria Central"]
    assert openai.chat_phrases == [["Padaria Central"]]
    channels = {channel for channel, _, _ in history.appended}
    assert channels == {HistoryChannel.WHATSAPP}
    assert [item.role for _, _, item in history.appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


# --- Online-chat search flow -------------------------------------------------


def test_e2e_should_answer_online_chat_message_through_real_service(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Restaurante B")
    vectors = _FakeVectorRepository(
        matches=[VectorMatch(id="v2", score=0.93, text="Restaurante B", user_code="2")]
    )
    history = _FakeHistoryRepository(
        history=[MessageHistoryItem(role=MessageRole.USER, text="oi")]
    )
    service = _search_service(openai, vectors, history)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    client = TestClient(app)

    # Act
    response = client.post(
        "/chat",
        json={
            "message": "onde comer?",
            "user_code": "4567895465",
            "user_ip": "200.148.12.188",
        },
    )

    # Assert
    assert _sse_messages(response) == [INTRO, "Restaurante B"]
    channels = {channel for channel, _, _ in history.appended}
    assert channels == {HistoryChannel.ONLINE}


def test_e2e_should_search_only_in_the_category_of_the_question(semantic_cache_db: Any) -> None:
    # Arrange: a restaurant and a beauty salon registered in their own categories.
    openai = _FakeOpenAIService(answer="Padaria", category="ALIMENTAÇÃO")
    vectors = _FakeVectorRepository()
    categories = _category_service()
    registration = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=_FakeStorageRepository(),
        category_service=categories,
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(),
    )
    search = _search_service(openai, vectors, _FakeHistoryRepository(), None, categories)
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: registration
    app.dependency_overrides[get_search_service] = lambda: search
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    client = TestClient(app)
    client.post("/companies", json=_registration_payload("123", "Padaria Central"))
    openai.category = "BELEZA"
    client.post("/companies", json=_registration_payload("456", "Salao Bela"))
    openai.category = "ALIMENTAÇÃO"

    # Act
    response = client.post(
        "/chat", json={"message": "onde tem pao?", "user_code": "1", "user_ip": "200.0.0.9"}
    )

    # Assert: only the restaurant chunks reached the language model.
    assert _sse_messages(response) == [INTRO, "Padaria"]
    assert vectors.queried_categories == ["alimentacao"]
    phrases = openai.chat_phrases[0]
    assert phrases and all("Padaria Central" in phrase for phrase in phrases)


def _chat_once(service: SearchService) -> None:
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    TestClient(app).post(
        "/chat", json={"message": "onde comer?", "user_code": "1", "user_ip": "200.0.0.9"}
    )


@pytest.mark.asyncio
async def test_e2e_should_store_question_category_slug_in_semantic_cache(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    openai = _FakeOpenAIService(category="ALIMENTAÇÃO")
    categories = _category_service()
    await categories.seed_initial()
    service = _search_service(
        openai, _FakeVectorRepository(), _FakeHistoryRepository(), None, categories
    )

    # Act
    _chat_once(service)

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == ["alimentacao"]


@pytest.mark.asyncio
async def test_e2e_should_store_null_category_when_search_runs_without_filter(
    semantic_cache_db: Any,
) -> None:
    # Arrange: the model answers with a category that is not in the catalog.
    openai = _FakeOpenAIService(category="INEXISTENTE")
    categories = _category_service()
    await categories.seed_initial()
    service = _search_service(
        openai, _FakeVectorRepository(), _FakeHistoryRepository(), None, categories
    )

    # Act
    _chat_once(service)

    # Assert
    assert [row["category"] for row in semantic_cache_db.rows] == [None]


# --- Global error handling (safe, standardized responses) --------------------


def test_e2e_should_return_safe_envelope_for_infrastructure_error(semantic_cache_db: Any) -> None:
    # Arrange: the vector store fails while answering a WhatsApp message.
    openai = _FakeOpenAIService()
    vectors = _FakeVectorRepository(fail_query=True)
    history = _FakeHistoryRepository()
    service = _search_service(openai, vectors, history)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    client = TestClient(app)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert: generic 500 envelope, no internal detail leaked.
    assert response.status_code == 500
    body = response.json()
    assert body["status_code"] == 500
    assert body["errors"] == ["internal_error"]
    assert body["message"] == "An unexpected error occurred."
    assert "Failed to query vectors" not in body["message"]


def test_e2e_should_return_safe_envelope_for_unexpected_error() -> None:
    # Arrange: an unexpected (non-domain) error bubbles out of the service.
    class _BrokenSearchService:
        async def search(
            self, channel: HistoryChannel, user_key: str, question: str
        ) -> list[str]:
            raise ValueError("unexpected boom with internal detail")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: _BrokenSearchService()
    client = TestClient(app, raise_server_exceptions=False)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert: still the generic 500 envelope, no internal detail leaked.
    assert response.status_code == 500
    body = response.json()
    assert body["errors"] == ["internal_error"]
    assert body["message"] == "An unexpected error occurred."
    assert "boom" not in body["message"]


# --- Answer cache flow ---------------------------------------------------------


def _online_chat_body(message: str, user_code: str = "4567895465") -> dict:
    return {"message": message, "user_code": user_code, "user_ip": "200.148.12.188"}


def _answer_keys(client: TestClient, redis_client: FakeAsyncRedis) -> list[str]:
    """Redis keys of the cached answers, without the category index SETs."""
    keys = client.portal.call(redis_client.keys, f"{ANSWER_CACHE_KEY_PREFIX}:*")
    return [key for key in keys if not key.startswith(ANSWER_CACHE_CATEGORY_PREFIX)]


def _indexed_answer_keys(
    client: TestClient, redis_client: FakeAsyncRedis
) -> dict[str | None, set[str]]:
    """Answer keys of each category index SET (``None`` for the uncategorized one)."""
    indexed: dict[str | None, set[str]] = {}
    for set_key in client.portal.call(redis_client.keys, f"{ANSWER_CACHE_CATEGORY_PREFIX}:*"):
        slug = set_key.removeprefix(f"{ANSWER_CACHE_CATEGORY_PREFIX}:")
        members = client.portal.call(redis_client.smembers, set_key)
        category = None if slug == UNCATEGORIZED_SLUG else slug
        indexed[category] = {f"{ANSWER_CACHE_KEY_PREFIX}:{member}" for member in members}
    return indexed


def test_e2e_should_answer_repeated_question_from_cache(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Restaurante B")
    vectors = _FakeVectorRepository(
        matches=[VectorMatch(id="v2", score=0.93, text="Restaurante B", user_code="2")]
    )
    history = _FakeHistoryRepository()
    redis_client = FakeAsyncRedis(decode_responses=True)
    service = _search_service(openai, vectors, history, redis_client)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()

    # Act
    with TestClient(app) as client:
        first = client.post("/chat", json=_online_chat_body("Onde comer?"))
        second = client.post("/chat", json=_online_chat_body("  onde COMER? "))
        keys = _answer_keys(client, redis_client)
        ttl = client.portal.call(redis_client.ttl, keys[0])

    # Assert: same answer, but OpenAI chat and embedding were called only once.
    assert _sse_messages(first) == _sse_messages(second) == [INTRO, "Restaurante B"]
    assert len(openai.chat_phrases) == 1
    assert openai.embedded_questions == ["onde comer?"]
    assert len(keys) == 1
    assert ANSWER_CACHE_TTL_SECONDS - 10 < ttl <= ANSWER_CACHE_TTL_SECONDS
    assert [item.role for _, _, item in history.appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


def test_e2e_should_share_cache_between_whatsapp_and_online_chat(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Padaria Central")
    matches = [VectorMatch(id="v1", score=0.95, text="Padaria Central", user_code="1")]
    service = _search_service(
        openai, _FakeVectorRepository(matches=matches), _FakeHistoryRepository()
    )
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()

    # Act
    with TestClient(app) as client:
        whatsapp = client.post(
            "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
        )
        online = client.post("/chat", json=_online_chat_body("onde comer?"))

    # Assert
    assert _sse_messages(whatsapp) == _sse_messages(online) == [INTRO, "Padaria Central"]
    assert len(openai.chat_phrases) == 1


# --- Semantic cache flow -------------------------------------------------------


def test_e2e_should_answer_from_semantic_then_exact_cache(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Marmitaria Central")
    vectors = _FakeVectorRepository(
        matches=[VectorMatch(id="v3", score=0.94, text="Marmitaria Central", user_code="3")]
    )
    history = _FakeHistoryRepository()
    redis_client = FakeAsyncRedis(decode_responses=True)
    service = _search_service(openai, vectors, history, redis_client)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()

    # Act
    with TestClient(app) as client:
        # 1) full miss: RAG + LLM, stored in Redis and PostgreSQL.
        first = client.post("/chat", json=_online_chat_body("Onde vende marmitas?"))
        rows_after_first = len(semantic_cache_db.rows)
        # 2) similar question: semantic hit, populates Redis for the new key.
        second = client.post("/chat", json=_online_chat_body("Onde posso comprar marmitas?"))
        selects_after_second = semantic_cache_db.select_count
        # 3) question 2 again: exact hit, PostgreSQL not queried.
        third = client.post("/chat", json=_online_chat_body("Onde posso comprar marmitas?"))
        keys = _answer_keys(client, redis_client)
        indexed = _indexed_answer_keys(client, redis_client)

    # Assert
    messages = [_sse_messages(response) for response in (first, second, third)]
    assert messages == [[INTRO, "Marmitaria Central"]] * 3
    assert len(openai.chat_phrases) == 1
    assert rows_after_first == 1
    assert len(semantic_cache_db.rows) == 1
    assert len(keys) == 2
    # The semantic-hit answer is indexed under the category of the reused entry.
    category = semantic_cache_db.rows[0]["category"]
    assert indexed == {category: set(keys)}
    assert selects_after_second == 2
    assert semantic_cache_db.select_count == 2
    assert openai.embedded_questions == ["onde vende marmitas?", "onde posso comprar marmitas?"]
    assert len(history.appended) == 6


# --- Semantic cache invalidation cycle ----------------------------------------


def _cycle_client(
    semantic_cache_db: Any, redis_client: FakeAsyncRedis | None = None
) -> tuple[TestClient, _FakeOpenAIService]:
    """Real registration, deletion and search services sharing catalog and caches."""
    openai = _FakeOpenAIService(answer="Padaria Central", category="ALIMENTAÇÃO")
    vectors = _FakeVectorRepository()
    categories = _category_service()
    asyncio.run(categories.seed_initial())
    redis_client = redis_client or FakeAsyncRedis(decode_responses=True)
    registration = RegistrationService(
        openai_service=openai,
        vector_repository=vectors,
        storage_repository=_FakeStorageRepository(),
        category_service=categories,
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(redis_client),
    )
    deletion = DeletionService(
        vector_repository=vectors,
        storage_repository=_FakeStorageRepository(),
        semantic_cache=_semantic_cache(),
        answer_cache=_answer_cache(redis_client),
    )
    search = _search_service(openai, vectors, _FakeHistoryRepository(), redis_client, categories)
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: registration
    app.dependency_overrides[get_deletion_service] = lambda: deletion
    app.dependency_overrides[get_search_service] = lambda: search
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    return TestClient(app), openai


def test_e2e_should_skip_semantic_cache_after_registration_in_same_category(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    client, openai = _cycle_client(semantic_cache_db)
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    client.post("/chat", json=_online_chat_body("Onde posso comer pao?"))
    assert len(openai.chat_phrases) == 1  # second question hit the semantic cache
    assert [row["category"] for row in semantic_cache_db.rows] == ["alimentacao"]

    # Act
    response = client.post("/companies", json=_registration_payload("123", "Padaria Nova"))
    client.post("/chat", json=_online_chat_body("Qual padaria fica perto?"))

    # Assert: the cached rows are gone, so the pipeline ran again.
    assert response.status_code == 201
    assert len(openai.chat_phrases) == 2


def test_e2e_should_skip_semantic_cache_after_deleting_client_of_the_category(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    client, openai = _cycle_client(semantic_cache_db)
    client.post("/companies", json=_registration_payload("123"))
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    assert [row["category"] for row in semantic_cache_db.rows] == ["alimentacao"]
    calls_before = len(openai.chat_phrases)

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})
    client.post("/chat", json=_online_chat_body("Onde posso comer pao?"))

    # Assert
    assert response.status_code == 200
    assert len(openai.chat_phrases) == calls_before + 1


def test_e2e_should_keep_other_category_entries_after_registration_and_deletion(
    semantic_cache_db: Any,
) -> None:
    # Arrange: a beauty answer cached before the food category changes.
    client, openai = _cycle_client(semantic_cache_db)
    openai.category = "BELEZA"
    client.post("/chat", json=_online_chat_body("Onde cortar cabelo?"))
    openai.category = "ALIMENTAÇÃO"
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza"]

    # Act
    client.post("/companies", json=_registration_payload("123"))
    client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert: the beauty row survived; a similar question is still a semantic hit.
    assert [row["category"] for row in semantic_cache_db.rows] == ["beleza"]
    calls_before = len(openai.chat_phrases)
    client.post("/chat", json=_online_chat_body("Onde posso cortar o cabelo?"))
    assert len(openai.chat_phrases) == calls_before


# --- Exact cache invalidation cycle -------------------------------------------


def _cached_answer_keys(redis_client: FakeAsyncRedis) -> list[str]:
    """Redis keys of the cached answers, read outside any running request."""

    async def _keys() -> list[str]:
        keys = await redis_client.keys(f"{ANSWER_CACHE_KEY_PREFIX}:*")
        return [key for key in keys if not key.startswith(ANSWER_CACHE_CATEGORY_PREFIX)]

    return asyncio.run(_keys())


def test_e2e_should_miss_exact_cache_after_registration_in_same_category(
    semantic_cache_db: Any,
) -> None:
    # Arrange: the question is answered once and then served by the exact cache.
    client, openai = _cycle_client(semantic_cache_db)
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    assert len(openai.chat_phrases) == 1

    # Act
    response = client.post("/companies", json=_registration_payload("123", "Padaria Nova"))
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))

    # Assert: the exact (and semantic) answers are gone, so the pipeline ran again.
    assert response.status_code == 201
    assert len(openai.chat_phrases) == 2


def test_e2e_should_miss_exact_cache_after_deleting_client_of_the_category(
    semantic_cache_db: Any,
) -> None:
    # Arrange
    client, openai = _cycle_client(semantic_cache_db)
    client.post("/companies", json=_registration_payload("123"))
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    calls_before = len(openai.chat_phrases)

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))

    # Assert
    assert response.status_code == 200
    assert len(openai.chat_phrases) == calls_before + 1


def test_e2e_should_keep_exact_answer_of_other_category_after_registration_and_deletion(
    semantic_cache_db: Any,
) -> None:
    # Arrange: a beauty answer cached before the food category changes.
    client, openai = _cycle_client(semantic_cache_db)
    openai.category = "BELEZA"
    client.post("/chat", json=_online_chat_body("Onde cortar cabelo?"))
    openai.category = "ALIMENTAÇÃO"

    # Act
    client.post("/companies", json=_registration_payload("123"))
    client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert: the same beauty question is an exact hit (no LLM, no semantic lookup).
    openai.category = "BELEZA"
    calls_before = len(openai.chat_phrases)
    selects_before = semantic_cache_db.select_count
    response = client.post("/chat", json=_online_chat_body("Onde cortar cabelo?"))
    assert _sse_messages(response) == [INTRO, "Padaria Central"]
    assert len(openai.chat_phrases) == calls_before
    assert semantic_cache_db.select_count == selects_before


def test_e2e_should_invalidate_exact_answers_of_both_categories_when_client_moves(
    semantic_cache_db: Any,
) -> None:
    # Arrange: client in beleza; one cached answer in beleza and one in alimentacao.
    redis_client = FakeAsyncRedis(decode_responses=True)
    client, openai = _cycle_client(semantic_cache_db, redis_client)
    openai.category = "BELEZA"
    client.post("/companies", json=_registration_payload("123", "Salao"))
    client.post("/chat", json=_online_chat_body("Onde cortar cabelo?"))
    openai.category = "ALIMENTAÇÃO"
    client.post("/chat", json=_online_chat_body("Onde comer pao?"))
    assert len(_cached_answer_keys(redis_client)) == 2

    # Act: the client moves from beleza to alimentacao.
    response = client.post("/companies", json=_registration_payload("123", "Padaria"))

    # Assert
    assert response.status_code == 201
    assert _cached_answer_keys(redis_client) == []


# --- Short messages -----------------------------------------------------------


def test_e2e_should_keep_short_message_out_of_history(semantic_cache_db: Any) -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Restaurante B")
    vectors = _FakeVectorRepository(
        matches=[VectorMatch(id="v2", score=0.93, text="Restaurante B", user_code="2")]
    )
    history = _FakeHistoryRepository()
    service = _search_service(openai, vectors, history)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    client = TestClient(app)

    # Act
    short = client.post("/chat", json=_online_chat_body("..."))
    valid = client.post("/chat", json=_online_chat_body("onde comer?"))

    # Assert
    short_messages = _sse_messages(short)
    assert len(short_messages) == 1
    assert short_messages[0] in search_service._INVALID_MESSAGE_RESPONSES
    assert _sse_messages(valid) == [INTRO, "Restaurante B"]
    assert openai.embedded_questions == ["onde comer?"]
    stored_texts = [message.text for _, _, message in history.appended]
    assert "..." not in stored_texts
    assert stored_texts[0] == "onde comer?"
