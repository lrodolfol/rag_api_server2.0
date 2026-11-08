"""WhatsApp search route.

Thin HTTP handler that delegates the whole retrieval-augmented-generation flow
to the shared :class:`SearchService`, using the WhatsApp history channel and the
sender's number as the per-user history key. The ready-made messages are
streamed back as Server-Sent Events; the search runs before the stream is
created, so its errors still become the standard :class:`ApiResponse` envelope.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_search_service
from app.api.patterns.streaming import SSE_OPENAPI_RESPONSES, sse_response
from app.application.search import SearchService
from app.domain import WhatsAppSearchPayload
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis import HistoryChannel

router = APIRouter(tags=["search"])
logger = get_logger(__name__)


@router.post(
    "/whatsapp", response_class=StreamingResponse, responses=SSE_OPENAPI_RESPONSES
)
async def search_whatsapp(
    payload: WhatsAppSearchPayload,
    service: SearchService = Depends(get_search_service),
) -> StreamingResponse:
    """Answer a WhatsApp message through the shared RAG pipeline."""
    logger.info("WhatsApp message received")
    messages = await service.search(
        HistoryChannel.WHATSAPP, payload.number, payload.text
    )
    logger.info("WhatsApp response sent")
    return sse_response(messages)
