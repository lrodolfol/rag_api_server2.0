"""Unit tests for :class:`CategoryService` with a mocked category repository."""

import logging
from unittest.mock import AsyncMock

import pytest

from app.application.categories import CategoryService
from app.domain import Category
from app.infrastructure.config import CategoriesConfig

CATALOG = ["ALIMENTAÇÃO", "CASA E MANUTENÇÃO", "SERVIÇOS PROFISSIONAIS"]
CONFIG = CategoriesConfig(redis_key="knowledge_categories", initial=CATALOG, fallback="OUTROS")


@pytest.fixture
def repository() -> AsyncMock:
    mock = AsyncMock()
    mock.get_all.return_value = list(CATALOG)
    return mock


@pytest.fixture
def service(repository: AsyncMock) -> CategoryService:
    return CategoryService(repository=repository, config=CONFIG)


@pytest.mark.asyncio
async def test_should_list_catalog_names(service: CategoryService) -> None:
    # Act / Assert
    assert await service.list_names() == CATALOG


@pytest.mark.asyncio
async def test_should_seed_configured_initial_categories(
    service: CategoryService, repository: AsyncMock
) -> None:
    # Act
    await service.seed_initial()

    # Assert
    repository.seed.assert_awaited_once_with(CATALOG)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("alimentacao", "ALIMENTAÇÃO"),
        ("Alimentação", "ALIMENTAÇÃO"),
        ("  servicos profissionais ", "SERVIÇOS PROFISSIONAIS"),
    ],
)
async def test_should_find_catalog_category_by_slug(
    service: CategoryService, repository: AsyncMock, name: str, expected: str
) -> None:
    # Act
    category = await service.find(name)

    # Assert
    assert category == Category.from_name(expected)
    repository.add.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["inexistente", "", "   ", "!!!"])
async def test_should_return_none_without_writing_when_not_found(
    service: CategoryService, repository: AsyncMock, name: str
) -> None:
    # Act
    category = await service.find(name)

    # Assert
    assert category is None
    repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_return_none_when_catalog_is_empty(
    service: CategoryService, repository: AsyncMock
) -> None:
    # Arrange
    repository.get_all.return_value = []

    # Act / Assert
    assert await service.find("alimentacao") is None


@pytest.mark.asyncio
async def test_should_resolve_existing_category_without_writing(
    service: CategoryService, repository: AsyncMock
) -> None:
    # Act
    category = await service.resolve_or_create("casa e manutencao")

    # Assert
    assert category.name == "CASA E MANUTENÇÃO"
    repository.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_should_create_missing_category_and_log_its_name(
    service: CategoryService, repository: AsyncMock, caplog: pytest.LogCaptureFixture
) -> None:
    # Act
    with caplog.at_level(logging.INFO):
        category = await service.resolve_or_create("PetShop")

    # Assert
    assert category == Category(name="PETSHOP", slug="petshop")
    repository.add.assert_awaited_once_with("PETSHOP")
    assert "New category added to the catalog: 'PETSHOP'" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["", "   ", "?!"])
async def test_should_resolve_blank_name_to_fallback(
    service: CategoryService, repository: AsyncMock, name: str
) -> None:
    # Act
    category = await service.resolve_or_create(name)

    # Assert
    assert category == Category(name="OUTROS", slug="outros")
    repository.add.assert_awaited_once_with("OUTROS")


@pytest.mark.asyncio
async def test_should_not_recreate_fallback_already_in_catalog(
    service: CategoryService, repository: AsyncMock
) -> None:
    # Arrange
    repository.get_all.return_value = [*CATALOG, "OUTROS"]

    # Act
    category = await service.resolve_or_create("")

    # Assert
    assert category.slug == "outros"
    repository.add.assert_not_awaited()
