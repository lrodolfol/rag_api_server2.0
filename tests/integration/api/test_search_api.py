"""Integration tests for the WhatsApp and online-chat search endpoints.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``. Most tests
replace the shared search service with a fake via dependency override; the
pipeline tests at the end wire the real :class:`SearchService` with OpenAI and
Pinecone mocked, the answer cache on ``fakeredis`` and the real semantic cache
on an in-memory PostgreSQL (``semantic_cache_db`` fixture), so no external
provider is contacted. The online-chat endpoint uses a real in-memory rate limiter (with
a small window) to exercise the blocking path.
"""

from typing import Any
from unittest.mock import AsyncMock

import psycopg
import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api.dependencies import get_rate_limiter, get_search_service
from app.application.cache import SemanticCacheService
from app.application.search import SearchService
from app.application.search import service as search_service
from app.infrastructure.config import FingerPrintConfig, PostgresConfig, SemanticCacheConfig
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import HistoryChannel, RedisAnswerCacheRepository
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


class _FakeSearchService:
    """In-memory stand-in recording searches and returning a fixed answer."""

    def __init__(self, answer: str = "Padaria Central") -> None:
        self._answer = answer
        self.calls: list[tuple[HistoryChannel, str, str]] = []

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> str:
        self.calls.append((channel, user_key, question))
        return self._answer


def _client(
    service: _FakeSearchService,
    limiter: InMemoryRateLimiter | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    if limiter is not None:
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
    return TestClient(app)


def test_should_answer_whatsapp_message_with_standard_envelope() -> None:
    # Arrange
    service = _FakeSearchService(answer="Padaria Central")
    client = _client(service)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == 200
    assert body["message"] == "Padaria Central"
    assert body["errors"] == []
    assert service.calls == [(HistoryChannel.WHATSAPP, "5535999999999", "onde comer?")]


def test_should_reject_invalid_whatsapp_payload_with_validation_error() -> None:
    # Arrange
    service = _FakeSearchService()
    client = _client(service)

    # Act
    response = client.post("/whatsapp", json={"number": "5535999999999"})

    # Assert
    assert response.status_code == 422
    assert service.calls == []


def test_should_answer_online_chat_message_with_standard_envelope() -> None:
    # Arrange
    service = _FakeSearchService(answer="Restaurante B")
    client = _client(service, InMemoryRateLimiter())

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
    body = response.json()
    assert body["message"] == "Restaurante B"
    assert service.calls == [(HistoryChannel.ONLINE, "4567895465", "onde comer?")]


def test_should_block_online_chat_after_limit_with_standard_envelope() -> None:
    # Arrange: max 3 messages per window, all from the same IP.
    service = _FakeSearchService()
    client = _client(service, InMemoryRateLimiter(max_messages=3))
    payload = {
        "message": "onde comer?",
        "user_code": "4567895465",
        "user_ip": "200.148.12.188",
    }

    # Act
    allowed = [client.post("/chat", json=payload).status_code for _ in range(3)]
    blocked = client.post("/chat", json=payload)

    # Assert
    assert allowed == [200, 200, 200]
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["status_code"] == 429
    assert "rate_limit_exceeded" in body["errors"]
    assert len(service.calls) == 3


def test_should_rate_limit_each_ip_independently() -> None:
    # Arrange
    service = _FakeSearchService()
    client = _client(service, InMemoryRateLimiter(max_messages=1))

    # Act
    first_ip = client.post(
        "/chat",
        json={"message": "a", "user_code": "1", "user_ip": "200.0.0.1"},
    )
    second_ip = client.post(
        "/chat",
        json={"message": "b", "user_code": "2", "user_ip": "200.0.0.2"},
    )

    # Assert: distinct IPs each get their own window.
    assert first_ip.status_code == 200
    assert second_ip.status_code == 200


# --- Real search pipeline with mocked providers --------------------------------

FINGER_PRINT = FingerPrintConfig(
    prompt_version="1.0.0", rules_version="1.0.0", model_capability="economic"
)
EMBEDDING = [0.1, 0.2, 0.3]
DISTANT_EMBEDDING = [0.3, -0.2, 0.1]
UNRELATED_QUESTION = "Onde tem pizza?"
RAW_QUESTION = "  Onde VOCÊ vende   marmitas "
NORMALIZED_QUESTION = "onde voce vende marmitas"


POSTGRES_CONFIG = PostgresConfig(
    host="localhost", port=5432, database="rag_auth", user="postgres", password="pw"
)
SEMANTIC_CACHE_CONFIG = SemanticCacheConfig(table="rag_response_cache", top_k=3)


class _Pipeline:
    """Real :class:`SearchService` wired to mocked OpenAI, Pinecone and history."""

    def __init__(self) -> None:
        self.openai = AsyncMock()
        self.openai.generate_embedding_for_question.return_value = EMBEDDING
        self.openai.generate_chat_answer.return_value = "Marmitaria Central"
        self.vectors = AsyncMock()
        self.vectors.query.return_value = [
            VectorMatch(id="v1", score=0.95, text="Marmitaria Central", user_code="1")
        ]
        self.history = AsyncMock()
        self.history.get_history.return_value = []
        self.redis = FakeAsyncRedis(decode_responses=True)
        self.service = SearchService(
            openai_service=self.openai,
            vector_repository=self.vectors,
            history_repository=self.history,
            answer_cache=RedisAnswerCacheRepository(self.redis),
            semantic_cache=SemanticCacheService(
                PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)
            ),
            fingerprint_config=FINGER_PRINT,
        )

    def client(self) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_search_service] = lambda: self.service
        app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
        return TestClient(app)


def _post_question(client: TestClient, endpoint: str, question: str) -> dict:
    if endpoint == "/whatsapp":
        body = {"number": "5535999999999", "text": question}
    else:
        body = {"message": question, "user_code": "1", "user_ip": "200.0.0.1"}
    return client.post(endpoint, json=body).json()


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_embed_normalized_question_once_through_endpoint(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        body = _post_question(client, endpoint, RAW_QUESTION)

    # Assert
    assert body["message"] == _with_intro("Marmitaria Central")
    pipeline.openai.generate_embedding_for_question.assert_awaited_once_with(
        NORMALIZED_QUESTION
    )
    pipeline.vectors.query.assert_awaited_once_with(EMBEDDING)
    payload, _ = pipeline.openai.generate_chat_answer.await_args.args
    assert payload.question == RAW_QUESTION


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_not_embed_again_when_answer_is_cached(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        _post_question(client, endpoint, RAW_QUESTION)
        body = _post_question(client, endpoint, NORMALIZED_QUESTION)

    # Assert
    assert body["message"] == _with_intro("Marmitaria Central")
    pipeline.openai.generate_embedding_for_question.assert_awaited_once()


# --- Semantic cache through the endpoints ---------------------------------------

SIMILAR_QUESTION = "Onde posso comprar marmitas?"


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_store_answer_in_both_caches_on_semantic_miss(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        body = _post_question(client, endpoint, RAW_QUESTION)
        redis_keys = client.portal.call(pipeline.redis.keys, "*")

    # Assert
    assert body["message"] == _with_intro("Marmitaria Central")
    pipeline.openai.generate_chat_answer.assert_awaited_once()
    assert len(redis_keys) == 1
    assert len(semantic_cache_db.rows) == 1
    row = semantic_cache_db.rows[0]
    assert row["input_text"] == RAW_QUESTION
    assert row["normalized_text"] == NORMALIZED_QUESTION
    assert row["embedding"] == "[0.1,0.2,0.3]"


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_answer_similar_question_from_semantic_cache(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        _post_question(client, endpoint, RAW_QUESTION)
        body = _post_question(client, endpoint, SIMILAR_QUESTION)
        redis_keys = client.portal.call(pipeline.redis.keys, "*")

    # Assert: answered without RAG/LLM, Redis populated for the new question.
    assert body["message"] == _with_intro("Marmitaria Central")
    pipeline.openai.generate_chat_answer.assert_awaited_once()
    pipeline.vectors.query.assert_awaited_once()
    assert len(redis_keys) == 2
    assert len(semantic_cache_db.rows) == 1


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_run_rag_when_semantic_similarity_is_below_threshold(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange: the second embedding is far from the cached one (similarity < 0.91).
    pipeline = _Pipeline()
    pipeline.openai.generate_embedding_for_question.side_effect = [
        EMBEDDING,
        DISTANT_EMBEDDING,
    ]
    pipeline.openai.generate_chat_answer.side_effect = [
        "Marmitaria Central",
        "Pizzaria Bella",
    ]

    # Act
    with pipeline.client() as client:
        _post_question(client, endpoint, RAW_QUESTION)
        body = _post_question(client, endpoint, UNRELATED_QUESTION)

    # Assert: answered by the RAG pipeline and stored as a new semantic entry.
    assert body["message"] == _with_intro("Pizzaria Bella")
    assert pipeline.openai.generate_chat_answer.await_count == 2
    assert pipeline.vectors.query.await_count == 2
    assert len(semantic_cache_db.rows) == 2


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_not_query_semantic_cache_on_exact_hit(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        _post_question(client, endpoint, RAW_QUESTION)
        body = _post_question(client, endpoint, RAW_QUESTION)

    # Assert
    assert body["message"] == _with_intro("Marmitaria Central")
    assert semantic_cache_db.select_count == 1


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_answer_through_rag_when_postgres_fails(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    semantic_cache_db.error = psycopg.OperationalError("connection refused")
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        response_body = _post_question(client, endpoint, RAW_QUESTION)

    # Assert
    assert response_body["status_code"] == 200
    assert response_body["message"] == _with_intro("Marmitaria Central")
    pipeline.openai.generate_chat_answer.assert_awaited_once()
    assert semantic_cache_db.rows == []
