"""Integration tests for the WhatsApp and online-chat search endpoints.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``. Most tests
replace the shared search service with a fake via dependency override; the
pipeline tests at the end wire the real :class:`SearchService` with OpenAI and
Pinecone mocked, the answer cache on ``fakeredis`` and the real semantic cache
on an in-memory PostgreSQL (``semantic_cache_db`` fixture), so no external
provider is contacted. The online-chat endpoint uses a real in-memory rate limiter (with
a small window) to exercise the blocking path.

Successful answers are Server-Sent Events streams: the body is split into its
``data:`` events and each one is decoded back into its message. The delay
between events is set to zero so the tests never wait.
"""

import json
from typing import Any
from unittest.mock import AsyncMock

import psycopg
import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from httpx import Response

from app.api.dependencies import (
    get_category_service,
    get_rate_limiter,
    get_search_service,
)
from app.api.patterns import streaming
from app.application.cache import SemanticCacheService
from app.application.categories import CategoryService
from app.application.search import SearchService
from app.application.search import service as search_service
from app.domain import ChatAnswer, OpenIaException
from app.infrastructure.config import (
    CategoriesConfig,
    FingerPrintConfig,
    PostgresConfig,
    SemanticCacheConfig,
)
from app.infrastructure.postgres import PostgresSemanticCacheRepository
from app.infrastructure.pinecone import VectorMatch
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import (
    HistoryChannel,
    RedisAnswerCacheRepository,
    RedisCategoryRepository,
)
from app.main import create_app

INTRO = "Encontrei para você:"
NOT_FOUND = "Nada encontrado."


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
    """Decode the ``message`` of every SSE ``data:`` event in the body."""
    events = [event for event in response.text.split("\n\n") if event]
    assert all(event.startswith("data: ") for event in events)
    return [json.loads(event.removeprefix("data: "))["message"] for event in events]


def _assert_sse_response(response: Response) -> None:
    """Assert the status, content type and headers of a successful SSE answer."""
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"


class _FakeSearchService:
    """In-memory stand-in recording searches and returning a fixed answer."""

    def __init__(self, messages: list[str] | None = None) -> None:
        self._messages = messages if messages is not None else [INTRO, "Padaria Central"]
        self.calls: list[tuple[HistoryChannel, str, str]] = []

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> list[str]:
        self.calls.append((channel, user_key, question))
        return self._messages


def _client(
    service: _FakeSearchService,
    limiter: InMemoryRateLimiter | None = None,
) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: service
    if limiter is not None:
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
    return TestClient(app)


def test_should_stream_whatsapp_answer_as_sse_events_in_order() -> None:
    # Arrange
    service = _FakeSearchService([INTRO, "Padaria Central", "Café São João"])
    client = _client(service)

    # Act
    response = client.post(
        "/whatsapp", json={"number": "5535999999999", "text": "onde comer?"}
    )

    # Assert
    _assert_sse_response(response)
    assert response.text == (
        f'data: {{"message": "{INTRO}"}}\n\n'
        'data: {"message": "Padaria Central"}\n\n'
        'data: {"message": "Café São João"}\n\n'
    )
    assert service.calls == [(HistoryChannel.WHATSAPP, "5535999999999", "onde comer?")]


def test_should_reject_invalid_whatsapp_payload_with_validation_error() -> None:
    # Arrange
    service = _FakeSearchService()
    client = _client(service)

    # Act
    response = client.post("/whatsapp", json={"number": "5535999999999"})

    # Assert: validation error stays a JSON response (FastAPI default), not a stream.
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]
    assert service.calls == []


def test_should_stream_online_chat_answer_as_sse_events_in_order() -> None:
    # Arrange
    service = _FakeSearchService([INTRO, "Restaurante B"])
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
    _assert_sse_response(response)
    assert _sse_messages(response) == [INTRO, "Restaurante B"]
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
    assert blocked.headers["content-type"].startswith("application/json")
    body = blocked.json()
    assert body["status_code"] == 429
    assert "rate_limit_exceeded" in body["errors"]
    assert len(service.calls) == 3


class _FailingOpenAISearchService:
    """Search service whose OpenAI call fails before any message is produced."""

    async def search(
        self, channel: HistoryChannel, user_key: str, question: str
    ) -> list[str]:
        raise OpenIaException("OpenAI request failed with internal detail")


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_return_safe_envelope_instead_of_stream_when_openai_fails(
    endpoint: str,
) -> None:
    # Arrange
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: _FailingOpenAISearchService()
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
    client = TestClient(app)

    # Act
    response = _post(client, endpoint, "onde comer?")

    # Assert: the error happens before the stream, so the JSON envelope is kept.
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["status_code"] == 500
    assert body["errors"] == ["internal_error"]
    assert "internal detail" not in body["message"]


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
CATEGORIES_CONFIG = CategoriesConfig(
    redis_key="knowledge_categories", initial=["ALIMENTAÇÃO", "BELEZA"], fallback="OUTROS"
)


class _Pipeline:
    """Real :class:`SearchService` wired to mocked OpenAI, Pinecone and history."""

    def __init__(self) -> None:
        self.openai = AsyncMock()
        self.openai.generate_embedding_for_question.return_value = EMBEDDING
        self.openai.generate_chat_answer.return_value = ChatAnswer(respostas=["Marmitaria Central"])
        self.openai.classify_question.return_value = "ALIMENTAÇÃO"
        self.vectors = AsyncMock()
        self.vectors.query.return_value = [
            VectorMatch(id="v1", score=0.95, text="Marmitaria Central", user_code="1")
        ]
        self.history = AsyncMock()
        self.history.get_history.return_value = []
        self.redis = FakeAsyncRedis(decode_responses=True)
        # Catalog on its own in-memory Redis (seeded by the app lifespan) so the
        # answer-cache key assertions only see cache keys.
        category_redis = FakeAsyncRedis(decode_responses=True)
        self.categories = CategoryService(
            RedisCategoryRepository(category_redis, CATEGORIES_CONFIG), CATEGORIES_CONFIG
        )
        self.service = SearchService(
            openai_service=self.openai,
            vector_repository=self.vectors,
            history_repository=self.history,
            answer_cache=RedisAnswerCacheRepository(self.redis),
            semantic_cache=SemanticCacheService(
                PostgresSemanticCacheRepository(POSTGRES_CONFIG, SEMANTIC_CACHE_CONFIG)
            ),
            fingerprint_config=FINGER_PRINT,
            category_service=self.categories,
        )

    def client(self) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_search_service] = lambda: self.service
        app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter()
        app.dependency_overrides[get_category_service] = lambda: self.categories
        return TestClient(app)


def _post(client: TestClient, endpoint: str, question: str) -> Response:
    if endpoint == "/whatsapp":
        body = {"number": "5535999999999", "text": question}
    else:
        body = {"message": question, "user_code": "1", "user_ip": "200.0.0.1"}
    return client.post(endpoint, json=body)


def _post_question(client: TestClient, endpoint: str, question: str) -> list[str]:
    response = _post(client, endpoint, question)
    _assert_sse_response(response)
    return _sse_messages(response)


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_embed_normalized_question_once_through_endpoint(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        messages = _post_question(client, endpoint, RAW_QUESTION)

    # Assert
    assert messages == [INTRO, "Marmitaria Central"]
    pipeline.openai.generate_embedding_for_question.assert_awaited_once_with(
        NORMALIZED_QUESTION
    )
    pipeline.vectors.query.assert_awaited_once_with(EMBEDDING, category_slug="alimentacao")
    payload, _ = pipeline.openai.generate_chat_answer.await_args.args
    assert payload.question == RAW_QUESTION


# --- Semantic cache through the endpoints ---------------------------------------

@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_store_answer_in_both_caches_on_semantic_miss(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        messages = _post_question(client, endpoint, RAW_QUESTION)
        redis_keys = client.portal.call(pipeline.redis.keys, "*")
        redis_value = client.portal.call(pipeline.redis.get, redis_keys[0])

    # Assert
    expected_json = ChatAnswer(respostas=["Marmitaria Central"]).to_json()
    assert messages == [INTRO, "Marmitaria Central"]
    pipeline.openai.generate_chat_answer.assert_awaited_once()
    assert len(redis_keys) == 1
    assert redis_value == expected_json
    assert len(semantic_cache_db.rows) == 1
    row = semantic_cache_db.rows[0]
    assert json.loads(row["response_json"]) == expected_json
    assert row["input_text"] == RAW_QUESTION
    assert row["normalized_text"] == NORMALIZED_QUESTION
    assert row["embedding"] == "[0.1,0.2,0.3]"


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
        ChatAnswer(respostas=["Marmitaria Central"]),
        ChatAnswer(respostas=["Pizzaria Bella"]),
    ]

    # Act
    with pipeline.client() as client:
        _post_question(client, endpoint, RAW_QUESTION)
        messages = _post_question(client, endpoint, UNRELATED_QUESTION)

    # Assert: answered by the RAG pipeline and stored as a new semantic entry.
    assert messages == [INTRO, "Pizzaria Bella"]
    assert pipeline.openai.generate_chat_answer.await_count == 2
    assert pipeline.vectors.query.await_count == 2
    assert len(semantic_cache_db.rows) == 2


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_answer_through_rag_when_postgres_fails(
    endpoint: str, semantic_cache_db: Any
) -> None:
    # Arrange
    semantic_cache_db.error = psycopg.OperationalError("connection refused")
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        response = _post(client, endpoint, RAW_QUESTION)

    # Assert
    _assert_sse_response(response)
    assert _sse_messages(response) == [INTRO, "Marmitaria Central"]
    pipeline.openai.generate_chat_answer.assert_awaited_once()
    assert semantic_cache_db.rows == []


# --- Short messages (answered without any LLM call) -------------------------


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
def test_should_stream_single_invalid_message_hint_for_short_message(endpoint: str) -> None:
    # Arrange: the real service; no PostgreSQL fixture is needed because a short
    # message never reaches the semantic cache. The short-message variations are
    # covered by the unit tests of ``is_short_message``.
    pipeline = _Pipeline()

    # Act
    with pipeline.client() as client:
        messages = _post_question(client, endpoint, "...")

    # Assert
    assert len(messages) == 1
    assert messages[0] in search_service._INVALID_MESSAGE_RESPONSES
    pipeline.openai.generate_embedding_for_question.assert_not_awaited()
    pipeline.openai.generate_chat_answer.assert_not_awaited()
    pipeline.vectors.query.assert_not_awaited()
    pipeline.history.get_history.assert_not_awaited()
    pipeline.history.append_message.assert_not_awaited()


def test_should_count_short_messages_towards_online_chat_rate_limit() -> None:
    # Arrange: max 2 messages per window, all from the same IP.
    pipeline = _Pipeline()
    limiter = InMemoryRateLimiter(max_messages=2)
    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: pipeline.service
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    client = TestClient(app)

    # Act
    allowed = [_post(client, "/chat", "...").status_code for _ in range(2)]
    blocked = _post(client, "/chat", "...")

    # Assert
    assert allowed == [200, 200]
    assert blocked.status_code == 429
    assert "rate_limit_exceeded" in blocked.json()["errors"]


@pytest.mark.parametrize("endpoint", ["/whatsapp", "/chat"])
@pytest.mark.parametrize(
    ("classification", "expected_slug"),
    [("ALIMENTAÇÃO", "alimentacao"), ("", None)],
)
def test_should_stream_answer_with_and_without_category_filter(
    semantic_cache_db: Any,
    endpoint: str,
    classification: str,
    expected_slug: str | None,
) -> None:
    # Arrange: unknown categories and classification failures are covered by the
    # SearchService unit tests.
    pipeline = _Pipeline()
    pipeline.openai.classify_question.return_value = classification

    # Act
    with pipeline.client() as client:
        messages = _post_question(client, endpoint, "onde tem marmita?")

    # Assert
    assert messages == [INTRO, "Marmitaria Central"]
    assert pipeline.openai.classify_question.await_args.args[1] == ["ALIMENTAÇÃO", "BELEZA"]
    pipeline.vectors.query.assert_awaited_once_with(EMBEDDING, category_slug=expected_slug)
