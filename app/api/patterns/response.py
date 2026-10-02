"""Standard API response envelope.

Every API endpoint returns this structure so clients can rely on a single,
predictable response shape.
"""

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    """Standard response envelope shared by all API endpoints."""

    status_code: int
    message: str
    errors: list[str] = Field(default_factory=list)
