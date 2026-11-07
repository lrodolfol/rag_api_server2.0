"""End-to-end integration tests for the three application flows.

Unlike the per-endpoint API tests (which replace the whole application service),
these exercise the *real* :class:`RegistrationService` and :class:`SearchService`
orchestration through the real routes, global exception handlers and response
envelope. Only the external dependencies (OpenAI, Pinecone, Redis, S3 and the
PostgreSQL semantic cache via the ``semantic_cache_db`` fixture) are replaced
with in-memory fakes, so the full application wiring is covered while no
external provider is contacted.
"""

from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_deletion_service,
    get_rate_limiter,
    get_registration_service,
    get_search_service,
)
from app.application.cache import SemanticCacheService
from app.application.deletion import DeletionService
from app.application.registration import RegistrationService
from app.application.search import SearchService
from app.application.search import service as search_service
from app.domain import (
    CompanyRegistrationRequest,
    EmbeddingRecord,
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
    VectorRepositoryError,
)
from app.infrastructure.config import FingerPrintConfig, PostgresConfig, SemanticCacheConfig
from app.infrastructure.openai.models import ModerationResult
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import (
    ANSWER_CACHE_KEY_PREFIX,
    ANSWER_CACHE_TTL_SECONDS,
    HistoryChannel,
    RedisAnswerCacheRepository,
)
from app.main import create_app


INTRO = "Encontrei para você:"
NOT_FOUND = "Nada encontrado."


@pytest.fixture(autouse=True)
def _fixed_search_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the random intro and not-found messages with a single fixed one."""
    monkeypatch.setattr(search_service, "_ANSWER_MESSAGES", (INTRO,))
    monkeypatch.setattr(search_service, "_NOT_FOUND_MESSAGES", (NOT_FOUND,))


def _with_intro(answer: str) -> str:
    return f"{INTRO}\n\n{answer}"


class _FakeOpenAIService:
    """In-memory stand-in for the OpenAI provider boundary."""

    def __init__(
        self, *, insult: bool = False, answer: str = "Padaria Central"
    ) -> None:
        self._insult = insult
        self._answer = answer
        self.chat_phrases: list[list[str]] = []
        self.embedded_questions: list[str] = []

    async def moderate(self, content: str) -> ModerationResult:
        return ModerationResult(insult=self._insult, insult_text=content if self._insult else "")

    async def generate_embeddings_from_chunks(
        self, chunks: list[str]
    ) -> list[EmbeddingRecord]:
        return [EmbeddingRecord(text=chunk, vector=[0.1, 0.2, 0.3]) for chunk in chunks]

    async def generate_embedding_for_question(self, question: str) -> list[float]:
        self.embedded_questions.append(question)
        return [0.1, 0.2, 0.3]

    async def generate_chat_answer(
        self, payload: PayloadQuestionOpenIA, phrases: list[str]
    ) -> str:
        self.chat_phrases.append(phrases)
        return self._answer


class _FakeVectorRepository:
    """In-memory stand-in for the Pinecone vector store."""

    def __init__(
        self, matches: list[VectorMatch] | None = None, *, fail_query: bool = False
    ) -> None:
        self._matches = matches or []
        self._fail_query = fail_query
        self.upserts: list[tuple[str, str, list[EmbeddingRecord]]] = []

    async def upsert_company_vectors(
        self, company_name: str, user_code: str, embeddings: list[EmbeddingRecord]
    ) -> None:
        self.upserts.append((company_name, user_code, embeddings))

    async def query(
        self, embedding: list[float], top_k: int = 5
    ) -> list[VectorMatch]:
        if self._fail_query:
            raise VectorRepositoryError("Failed to query vectors")
        return self._matches

    async def has_vectors_for_user_code(self, user_code: str) -> bool:
        return any(upsert[1] == user_code for upsert in self.upserts)

    async def delete_by_user_code(self, user_code: str) -> None:
        self.upserts = [upsert for upsert in self.upserts if upsert[1] != user_code]


class _FakeStorageRepository:
    """In-memory stand-in for the S3 client-record store."""

    def __init__(self) -> None:
        self.saved: list[CompanyRegistrationRequest] = []

    async def save_client(self, registration: CompanyRegistrationRequest) -> None:
        self.saved.append(registration)

    async def delete_client(self, user_code: str) -> None:
        self.saved = [item for item in self.saved if item.user_code != user_code]


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


def _search_service(
    openai: _FakeOpenAIService,
    vectors: _FakeVectorRepository,
    history: _FakeHistoryRepository,
    redis_client: FakeAsyncRedis | None = None,
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
        semantic_cache=SemanticCacheService(
            PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)
        ),
        fingerprint_config=FINGER_PRINT,
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


def test_e2e_should_register_company_through_real_service() -> None:
    # Arrange: real RegistrationService wired to fake external deps.
    openai = _FakeOpenAIService()
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    service = RegistrationService(
        openai_service=openai, vector_repository=vectors, storage_repository=storage
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
    assert len(storage.saved) == 1
    assert storage.saved[0].user_code == "123"


def test_e2e_should_reject_inappropriate_registration_without_persisting() -> None:
    # Arrange: moderation flags the content as inappropriate.
    openai = _FakeOpenAIService(insult=True)
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    service = RegistrationService(
        openai_service=openai, vector_repository=vectors, storage_repository=storage
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


def test_e2e_should_register_then_delete_company_through_real_services() -> None:
    # Arrange: real registration and deletion services sharing fake external deps.
    vectors = _FakeVectorRepository()
    storage = _FakeStorageRepository()
    registration = RegistrationService(
        openai_service=_FakeOpenAIService(),
        vector_repository=vectors,
        storage_repository=storage,
    )
    deletion = DeletionService(vector_repository=vectors, storage_repository=storage)
    app = create_app()
    app.dependency_overrides[get_registration_service] = lambda: registration
    app.dependency_overrides[get_deletion_service] = lambda: deletion
    client = TestClient(app)
    client.post("/companies", json=_registration_payload("123"))
    client.post("/companies", json=_registration_payload("456", "Floricultura"))

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "123"})

    # Assert: only the target client's vectors and record were removed.
    assert response.status_code == 200
    assert response.json()["status_code"] == 200
    assert [upsert[1] for upsert in vectors.upserts] == ["456"]
    assert [item.user_code for item in storage.saved] == ["456"]


def test_e2e_should_return_ok_when_deleting_unknown_company() -> None:
    # Arrange: nothing registered for the requested client.
    storage = _FakeStorageRepository()
    deletion = DeletionService(
        vector_repository=_FakeVectorRepository(), storage_repository=storage
    )
    app = create_app()
    app.dependency_overrides[get_deletion_service] = lambda: deletion
    client = TestClient(app)

    # Act
    response = client.request("DELETE", "/companies", json={"user_code": "999"})

    # Assert
    assert response.status_code == 200
    assert response.json()["errors"] == []


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
    assert response.status_code == 200
    assert response.json()["message"] == _with_intro("Padaria Central")
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
    assert response.status_code == 200
    assert response.json()["message"] == _with_intro("Restaurante B")
    channels = {channel for channel, _, _ in history.appended}
    assert channels == {HistoryChannel.ONLINE}


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
        ) -> str:
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
        keys = client.portal.call(redis_client.keys, f"{ANSWER_CACHE_KEY_PREFIX}:*")
        ttl = client.portal.call(redis_client.ttl, keys[0])

    # Assert: same answer, but OpenAI chat and embedding were called only once.
    assert first.json()["message"] == second.json()["message"] == _with_intro("Restaurante B")
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
    assert whatsapp.json()["message"] == online.json()["message"] == _with_intro("Padaria Central")
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
        keys = client.portal.call(redis_client.keys, f"{ANSWER_CACHE_KEY_PREFIX}:*")

    # Assert
    messages = [response.json()["message"] for response in (first, second, third)]
    assert messages == [_with_intro("Marmitaria Central")] * 3
    assert len(openai.chat_phrases) == 1
    assert rows_after_first == 1
    assert len(semantic_cache_db.rows) == 1
    assert len(keys) == 2
    assert selects_after_second == 2
    assert semantic_cache_db.select_count == 2
    assert openai.embedded_questions == ["onde vende marmitas?", "onde posso comprar marmitas?"]
    assert len(history.appended) == 6
