"""WhatsApp search route.

Thin HTTP handler that delegates the whole retrieval-augmented-generation flow
to the shared :class:`SearchService`, using the WhatsApp history channel and the
sender's number as the per-user history key.
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_search_service
from app.api.patterns.response import ApiResponse
from app.application.search import SearchService
from app.domain import WhatsAppSearchPayload
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis import HistoryChannel

router = APIRouter(tags=["search"])
logger = get_logger(__name__)


@router.post("/whatsapp", response_model=ApiResponse)
async def search_whatsapp(
    payload: WhatsAppSearchPayload,
    service: SearchService = Depends(get_search_service),
) -> ApiResponse:
    """Answer a WhatsApp message through the shared RAG pipeline."""
    logger.info("WhatsApp message received")
    answer = await service.search(
        HistoryChannel.WHATSAPP, payload.number, payload.text
    )
    logger.info("WhatsApp response sent")
    return ApiResponse(status_code=status.HTTP_200_OK, message=answer)
