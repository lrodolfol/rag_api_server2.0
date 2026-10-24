"""Online-chat search route.

Thin HTTP handler that first enforces the per-IP rate limit, then delegates the
retrieval-augmented-generation flow to the shared :class:`SearchService`, using
the online history channel and the caller's ``user_code`` as the per-user
history key. Exceeding the limit raises the domain :class:`RateLimitError`,
translated into the standard :class:`ApiResponse` envelope by the global
exception handlers (``app/api/errors``).
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_rate_limiter, get_search_service
from app.api.patterns.response import ApiResponse
from app.application.search import SearchService
from app.domain import OnlineChatSearchPayload
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.rate_limit import InMemoryRateLimiter
from app.infrastructure.redis import HistoryChannel

router = APIRouter(tags=["search"])
logger = get_logger(__name__)


@router.post("/chat", response_model=ApiResponse)
async def search_chat(
    payload: OnlineChatSearchPayload,
    service: SearchService = Depends(get_search_service),
    limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
) -> ApiResponse:
    """Answer an online-chat message, enforcing the per-IP rate limit first."""
    logger.info("Online chat message received from ip='%s'", payload.user_ip)
    await limiter.check_and_increment(str(payload.user_ip))
    answer = await service.search(
        HistoryChannel.ONLINE, payload.user_code, payload.message
    )
    logger.info("Online chat response sent to ip='%s'", payload.user_ip)
    return ApiResponse(status_code=status.HTTP_200_OK, message=answer)
