"""Integration test for the /health endpoint via the FastAPI test client."""

from fastapi.testclient import TestClient

from app.main import app


def test_should_return_success_envelope_on_health_check() -> None:
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["status_code"] == 200
    assert body["message"] == "healthy"
    assert body["errors"] == []
