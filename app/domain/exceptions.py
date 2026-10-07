"""Domain-specific exceptions.

These represent business errors that are meaningful inside the application
domain. They intentionally carry safe, human-readable messages and never expose
internal implementation details (stack traces, provider payloads, credentials).
"""


class DomainError(Exception):
    """Base class for every business error raised by the domain layer."""


class OpenIaException(DomainError):
    """Raised when an interaction with the OpenAI provider fails."""


class InappropriateContentError(DomainError):
    """Raised when submitted content contains insults or inappropriate text."""


class RateLimitError(DomainError):
    """Raised when a caller exceeds the allowed request/message limit."""


class VectorRepositoryError(DomainError):
    """Raised when an interaction with the vector database fails."""
