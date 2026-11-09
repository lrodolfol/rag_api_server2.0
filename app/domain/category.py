"""Knowledge-base category domain model.

A category has a display ``name`` (upper case, accents kept, e.g.
``SERVIÇOS PROFISSIONAIS``) and a ``slug`` (ASCII, lower case, ``_`` instead of
spaces, e.g. ``servicos_profissionais``). The name is what is stored in Redis
and shown to the LLM; the slug identifies the category in the bucket file name
and in the vector metadata. Two categories are the same when their slugs match.
"""

import re
import unicodedata
from typing import Final, Self

from pydantic import BaseModel, ConfigDict, Field

_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")
_NON_SLUG_CHARS: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_]")


class Category(BaseModel):
    """Immutable knowledge-base category (display name + slug)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)

    @classmethod
    def from_name(cls, name: str) -> Self:
        """Build a category from any spelling of its name.

        Raises ``pydantic.ValidationError`` when the name is blank or has no
        letter/digit left to build the slug from.
        """
        normalized_name = name.strip().upper()
        return cls(name=normalized_name, slug=slugify(normalized_name))


def slugify(name: str) -> str:
    """Return ``name`` without accents, lower case, with ``_`` instead of spaces."""
    decomposed = unicodedata.normalize("NFKD", name.strip())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    underscored = _WHITESPACE.sub("_", without_accents.lower())
    return _NON_SLUG_CHARS.sub("", underscored)
