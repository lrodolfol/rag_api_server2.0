"""Knowledge-base categories service.

Resolves any spelling of a category name to a category of the catalog kept in
Redis. Categories are compared by slug, so ``"Alimentação"`` and
``"ALIMENTACAO"`` are the same category.

- :meth:`CategoryService.find` only looks the category up (used by search);
- :meth:`CategoryService.resolve_or_create` also adds a missing category to the
  catalog, falling back to the configured category when the name is blank
  or has no letter/digit (used by registration).

Repository failures are already logged and handled (empty catalog on read,
ignored on write), so this service never breaks the caller.
"""

from app.domain import Category, slugify
from app.infrastructure.config import CategoriesConfig
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis import RedisCategoryRepository

logger = get_logger(__name__)


class CategoryService:
    """Look up, create and seed the knowledge-base categories."""

    def __init__(
        self, repository: RedisCategoryRepository, config: CategoriesConfig
    ) -> None:
        self._repository = repository
        self._config = config

    async def list_names(self) -> list[str]:
        """Return every category name of the catalog, alphabetically."""
        return await self._repository.get_all()

    async def seed_initial(self) -> None:
        """Load the configured initial categories into the catalog (idempotent)."""
        await self._repository.seed(self._config.initial)

    async def find(self, name: str) -> Category | None:
        """Return the catalog category matching ``name`` by slug, or ``None``."""
        if not slugify(name):
            return None
        wanted = Category.from_name(name)
        for catalog_name in await self.list_names():
            category = Category.from_name(catalog_name)
            if category.slug == wanted.slug:
                return category
        return None

    async def resolve_or_create(self, name: str) -> Category:
        """Return the catalog category for ``name``, adding it when missing.

        A blank ``name`` (or one without letters/digits) resolves to the
        configured ``fallback`` category.
        """
        effective_name = name if slugify(name) else self._config.fallback
        existing = await self.find(effective_name)
        if existing is not None:
            return existing
        category = Category.from_name(effective_name)
        await self._repository.add(category.name)
        logger.info("New category added to the catalog: '%s'", category.name)
        return category
