"""Business category entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str
    id: int | None = None
