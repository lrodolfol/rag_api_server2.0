"""Request/response schemas for the API layer."""

from pydantic import BaseModel, EmailStr, Field

MAX_MESSAGE_LENGTH = 1000
MAX_DESCRIPTION_LENGTH = 5000
MAX_NAME_LENGTH = 200
MAX_RESULTS = 5


class BusinessCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=20)
    whatsapp: str | None = Field(default=None, min_length=8, max_length=20)
    opening_hours: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    has_delivery: bool = False


class UserMessageRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class SearchResult(BaseModel):
    name: str
    description: str
    email_link: str | None = None
    phone_link: str | None = None
    whatsapp_link: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult] = Field(default_factory=list, max_length=MAX_RESULTS)
