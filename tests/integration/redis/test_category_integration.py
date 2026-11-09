"""Integration tests for the categories catalog with a fake Redis server.

``fakeredis`` provides an in-memory, protocol-accurate async server so the
catalog flow (seed, add, read and slug resolution) is exercised end to end
through the repository and the service, as in the other Redis integration tests.
"""

import pytest
from fakeredis import FakeAsyncRedis

from app.application.categories import CategoryService
from app.infrastructure.config import CategoriesConfig
from app.infrastructure.redis import RedisCategoryRepository

CONFIG = CategoriesConfig(
    redis_key="knowledge_categories",
    initial=["SAÚDE", "ALIMENTAÇÃO", "BELEZA"],
    fallback="OUTROS",
)


@pytest.fixture
def client() -> FakeAsyncRedis:
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def repository(client: FakeAsyncRedis) -> RedisCategoryRepository:
    return RedisCategoryRepository(client, CONFIG)


@pytest.mark.asyncio
async def test_should_not_duplicate_when_seeding_twice(
    repository: RedisCategoryRepository, client: FakeAsyncRedis
) -> None:
    # Act
    await repository.seed(CONFIG.initial)
    await repository.seed(CONFIG.initial)

    # Assert
    assert await client.scard(CONFIG.redis_key) == 3
    assert await repository.get_all() == ["ALIMENTAÇÃO", "BELEZA", "SAÚDE"]


@pytest.mark.asyncio
async def test_should_keep_added_categories_after_new_seed(
    repository: RedisCategoryRepository,
) -> None:
    # Arrange
    await repository.seed(CONFIG.initial)
    await repository.add("PETSHOP")

    # Act
    await repository.seed(CONFIG.initial)

    # Assert
    assert await repository.get_all() == ["ALIMENTAÇÃO", "BELEZA", "PETSHOP", "SAÚDE"]


@pytest.mark.asyncio
async def test_should_return_empty_list_when_catalog_does_not_exist(
    repository: RedisCategoryRepository,
) -> None:
    # Act / Assert
    assert await repository.get_all() == []


@pytest.mark.asyncio
async def test_should_resolve_find_and_create_through_redis(
    repository: RedisCategoryRepository,
) -> None:
    # Arrange
    service = CategoryService(repository=repository, config=CONFIG)
    await service.seed_initial()

    # Act
    found = await service.find("alimentacao")
    missing = await service.find("inexistente")
    created = await service.resolve_or_create("PetShop")
    fallback = await service.resolve_or_create("")

    # Assert
    assert found is not None and found.name == "ALIMENTAÇÃO"
    assert missing is None
    assert created.name == "PETSHOP"
    assert fallback.name == "OUTROS"
    assert await service.list_names() == [
        "ALIMENTAÇÃO",
        "BELEZA",
        "OUTROS",
        "PETSHOP",
        "SAÚDE",
    ]
