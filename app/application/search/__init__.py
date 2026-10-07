"""Search package.

Exposes the shared RAG search service that both the WhatsApp and online-chat
endpoints use to run the retrieval-augmented-generation pipeline.
"""

from app.application.search.service import SearchService

__all__ = ["SearchService"]
