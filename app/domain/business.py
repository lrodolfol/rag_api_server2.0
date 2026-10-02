"""Business (company/service) entity registered by a customer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Business:
    name: str
    description: str
    email: str
    phone: str
    whatsapp: str | None = None
    opening_hours: str | None = None
    has_delivery: bool = False
    category: str | None = None
    id: int | None = None
