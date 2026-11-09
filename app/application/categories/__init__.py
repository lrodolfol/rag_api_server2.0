"""Knowledge-base categories package.

Exposes the service that resolves category names against the Redis catalog.
"""

from app.application.categories.service import CategoryService

__all__ = ["CategoryService"]
