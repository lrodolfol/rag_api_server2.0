"""Integration tests: categories catalog seeding in the application lifespan.

The category service is overridden with one backed by an in-memory Redis (or a
failing client) so startup is exercised end to end without a real Redis.
"""

import logging
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.dependencies import get_category_service
from app.application.categories import CategoryService
from app.infrastructure.config import CategoriesConfig
from app.infrastructure.redis import RedisCategoryRepository
from app.main import create_app

CONFIG = CategoriesConfig(
    redis_key="knowledge_categories",
    initial=["SAÚDE", "ALIMENTAÇÃO"],
    fallback="OUTROS",
)


def _service(client: FakeAsyncRedis | AsyncMock) -> CategoryService:
    return CategoryService(repository=RedisCategoryRepository(client, CONFIG), config=CONFIG)


def test_should_seed_initial_categories_on_startup() -> None:
    # Arrange
    redis_client = FakeAsyncRedis(decode_responses=True)
    service = _service(redis_client)
    app = create_app()
    app.dependency_overrides[get_category_service] = lambda: service

    # Act
    with TestClient(app) as client:
        names = client.portal.call(service.list_names)

    # Assert
    assert names == ["ALIMENTAÇÃO", "SAÚDE"]


def test_should_start_when_redis_is_down(caplog: pytest.LogCaptureFixture) -> None:
    # Arrange
    redis_client = AsyncMock()
    redis_client.sadd.side_effect = RedisConnectionError("connection refused")
    redis_client.smembers.side_effect = RedisConnectionError("connection refused")
    service = _service(redis_client)
    app = create_app()
    app.dependency_overrides[get_category_service] = lambda: service
    # create_app() reconfigures the root logger, dropping the caplog handler.
    logging.getLogger().addHandler(caplog.handler)

    # Act
    with caplog.at_level(logging.ERROR), TestClient(app) as client:
        health = client.get("/health")
        names = client.portal.call(service.list_names)

    # Assert
    assert health.status_code == 200
    assert names == []
    assert "Failed to seed the categories catalog" in caplog.text
    assert "Failed to read the categories catalog" in caplog.text
    logging.getLogger().removeHandler(caplog.handler)
