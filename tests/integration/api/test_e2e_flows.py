"""End-to-end integration tests for the three application flows.

Unlike the per-endpoint API tests (which replace the whole application service),
these exercise the *real* :class:`RegistrationService` and :class:`SearchService`
orchestration through the real routes, global exception handlers and response
envelope. Only the external dependencies (OpenAI, Pinecone, Redis, S3) are
replaced with in-memory fakes, so the full application wiring is covered while no
external provider is contacted.
"""

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_rate_limiter,
    get_registration_service,
    get_search_service,
)
from app.application.registration import RegistrationService
from app.application.search import SearchService
from app.domain import (
    CompanyRegistrationRequest,
    EmbeddingRecord,
    MessageHistoryItem,
    MessageRole,
    PayloadQuestionOpenIA,
    VectorRepositoryError,
)
from app.infrastructure.openai.models import ModerationResult
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import HistoryChannel
from app.main import create_app


class _FakeOpenAIService:
    """In-memory stand-in for the OpenAI provider boundary."""

    def __init__(
        self, *, insult: bool = False, answer: str = "Padaria Central"
    ) -> None:
        self._insult = insult
        self._answer = answer
        self.chat_phrases: list[list[str]] = []

    async def moderate(self, content: str) -> ModerationResult:
        return ModerationResult(insult=self._insult, insult_text=content if self._insult else "")

    async def generate_embeddings_from_chunks(
        self, chunks: list[str]
    ) -> list[EmbeddingRecord]:
        return [EmbeddingRecord(text=chunk, vector=[0.1, 0.2, 0.3]) for chunk in chunks]

    async def generate_embedding_for_question(self, question: str) -> list[float]:
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


class _FakeStorageRepository:
    """In-memory stand-in for the S3 client-record store."""

    def __init__(self) -> None:
        self.saved: list[CompanyRegistrationRequest] = []

    async def save_client(self, registration: CompanyRegistrationRequest) -> None:
        self.saved.append(registration)


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


# --- WhatsApp search flow ----------------------------------------------------


def test_e2e_should_answer_whatsapp_message_through_real_service() -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Padaria Central")
    matches = [VectorMatch(id="v1", score=0.95, text="Padaria Central", user_code="1")]
    vectors = _FakeVectorRepository(matches=matches)
    history = _FakeHistoryRepository()
    service = SearchService(
        openai_service=openai, vector_repository=vectors, history_repository=history
    )
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    client = TestClient(app)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert: answer returned and the turn was persisted on the WhatsApp channel.
    assert response.status_code == 200
    assert response.json()["message"] == "Padaria Central"
    assert openai.chat_phrases == [["Padaria Central"]]
    channels = {channel for channel, _, _ in history.appended}
    assert channels == {HistoryChannel.WHATSAPP}
    assert [item.role for _, _, item in history.appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


# --- Online-chat search flow -------------------------------------------------


def test_e2e_should_answer_online_chat_message_through_real_service() -> None:
    # Arrange
    openai = _FakeOpenAIService(answer="Restaurante B")
    vectors = _FakeVectorRepository(
        matches=[VectorMatch(id="v2", score=0.93, text="Restaurante B", user_code="2")]
    )
    history = _FakeHistoryRepository(
        history=[MessageHistoryItem(role=MessageRole.USER, text="oi")]
    )
    service = SearchService(
        openai_service=openai, vector_repository=vectors, history_repository=history
    )
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
    assert response.json()["message"] == "Restaurante B"
    channels = {channel for channel, _, _ in history.appended}
    assert channels == {HistoryChannel.ONLINE}


# --- Global error handling (safe, standardized responses) --------------------


def test_e2e_should_return_safe_envelope_for_infrastructure_error() -> None:
    # Arrange: the vector store fails while answering a WhatsApp message.
    openai = _FakeOpenAIService()
    vectors = _FakeVectorRepository(fail_query=True)
    history = _FakeHistoryRepository()
    service = SearchService(
        openai_service=openai, vector_repository=vectors, history_repository=history
    )
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
