"""Chat answer domain model.

The language model answers with ``{"respostas": ["...", "..."]}``. ``ChatAnswer``
is the typed representation of that payload, shared by the search flow, the
exact (Redis) cache and the semantic (PostgreSQL) cache.
"""

import json
from typing import Self

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.domain.exceptions import InvalidChatAnswerError

ANSWER_ITEMS_KEY = "respostas"
DEFAULT_TEXT_SEPARATOR = "\n\n"


class ChatAnswer(BaseModel):
    """An answer made of ordered, non-blank text items."""

    respostas: list[str] = Field(default_factory=list)

    @field_validator("respostas")
    @classmethod
    def _drop_blank_items(cls, items: list[str]) -> list[str]:
        return [item.strip() for item in items if item.strip()]

    @classmethod
    def from_json(cls, raw: str) -> Self:
        """Parse ``{"respostas": [...]}`` JSON, raising ``InvalidChatAnswerError`` on bad input."""
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as error:
            raise InvalidChatAnswerError("Answer is not valid JSON") from error
        if not isinstance(payload, dict) or ANSWER_ITEMS_KEY not in payload:
            raise InvalidChatAnswerError(f"Answer JSON must contain '{ANSWER_ITEMS_KEY}'")
        try:
            return cls.model_validate(payload)
        except ValidationError as error:
            raise InvalidChatAnswerError("Answer JSON has an unexpected format") from error

    @classmethod
    def merge(cls, answers: list[Self]) -> Self:
        """Concatenate items in the given order, keeping only the first occurrence of each."""
        items = [item for answer in answers for item in answer.respostas]
        return cls(respostas=list(dict.fromkeys(items)))

    def to_json(self) -> str:
        """Serialize as ``{"respostas": [...]}`` keeping non-ASCII characters readable."""
        return json.dumps({ANSWER_ITEMS_KEY: self.respostas}, ensure_ascii=False)

    def is_empty(self) -> bool:
        """Return ``True`` when there are no items ('not found' answer)."""
        return not self.respostas

    def as_text(self, separator: str = DEFAULT_TEXT_SEPARATOR) -> str:
        """Join the items into a single readable text (used by the history)."""
        return separator.join(self.respostas)
