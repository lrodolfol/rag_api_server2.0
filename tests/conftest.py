"""Shared fixtures for the whole test suite.

The application lifespan seeds the categories catalog into Redis. Tests start
the app (``with TestClient(app)``) without a real Redis, so the default category
service is replaced by one backed by an in-memory Redis. Tests that need a
specific service still override ``get_category_service`` on the app.
"""

import pytest
from fakeredis import FakeAsyncRedis

from app.api import dependencies
from app.application.categories import CategoryService
from app.infrastructure.config import CategoriesConfig
from app.infrastructure.redis import RedisCategoryRepository

TEST_CATEGORIES_CONFIG = CategoriesConfig(
    redis_key="knowledge_categories", initial=["ALIMENTAÇÃO"], fallback="OUTROS"
)


def _in_memory_category_service() -> CategoryService:
    repository = RedisCategoryRepository(
        FakeAsyncRedis(decode_responses=True), TEST_CATEGORIES_CONFIG
    )
    return CategoryService(repository=repository, config=TEST_CATEGORIES_CONFIG)


@pytest.fixture(autouse=True)
def _in_memory_categories_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the lifespan seed away from the real Redis and configuration."""
    monkeypatch.setattr(dependencies, "_category_service", _in_memory_category_service)
