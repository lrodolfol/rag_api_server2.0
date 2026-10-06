"""Conversation domain models.

Model the message history exchanged with a user and the payload sent to the
language model. These are plain data structures; the actual provider call lives
in the infrastructure layer.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Who authored a message in the conversation history."""

    USER = "user"
    ASSISTANT = "assistant"


class MessageHistoryItem(BaseModel):
    """A single message in a user's conversation history."""

    role: MessageRole
    text: str = Field(min_length=1)

    @property
    def is_user(self) -> bool:
        """Whether the message was authored by the user."""
        return self.role is MessageRole.USER


class PayloadQuestionOpenIA(BaseModel):
    """Question plus prior history used to build a request to the LLM."""

    question: str
    chat_historic: list[MessageHistoryItem] = Field(default_factory=list)

    def is_invalid(self) -> bool:
        """Return ``True`` when the question is empty or blank."""
        return not self.question.strip()
