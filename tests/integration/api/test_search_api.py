"""Integration tests for the WhatsApp and online-chat search endpoints.

The HTTP layer is exercised end to end with a FastAPI ``TestClient``; the shared
search service is replaced with a fake via dependency override so no external
provider is contacted. The online-chat endpoint uses a real in-memory rate
limiter (with a small window) to exercise the blocking path.
"""

from fastapi.testclient import TestClient

from app.api.dependencies import get_rate_limiter, get_search_service
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import HistoryChannel
from app.main import create_app


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
