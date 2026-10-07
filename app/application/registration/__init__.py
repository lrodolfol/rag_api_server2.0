"""Company registration package.

Exposes the ingestion service that orchestrates moderation, chunking,
embedding, vector upsert and client-record storage for a registration.
"""

from app.application.registration.service import RegistrationService

__all__ = ["RegistrationService"]
