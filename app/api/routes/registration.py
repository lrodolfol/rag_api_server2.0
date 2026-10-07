"""Company registration route.

Thin HTTP handler that delegates the whole ingestion flow to
:class:`RegistrationService`. Inappropriate content raised by the service is
translated into the standard :class:`ApiResponse` envelope by a dedicated
exception handler, keeping the handler itself a single delegation and never
leaking the offending text back to the client.
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_registration_service
from app.api.patterns.response import ApiResponse
from app.application.registration import RegistrationService
from app.domain import CompanyRegistrationRequest, InappropriateContentError

router = APIRouter(tags=["registration"])


@router.post(
    "/companies",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    registration: CompanyRegistrationRequest,
    service: RegistrationService = Depends(get_registration_service),
) -> ApiResponse:
    """Register a company by running the full ingestion pipeline."""
    await service.register(registration)
    return ApiResponse(
        status_code=status.HTTP_201_CREATED,
        message="Company registered successfully",
    )


async def inappropriate_content_handler(
    _: Request, exception: InappropriateContentError
) -> JSONResponse:
    """Translate an inappropriate-content error into the standard envelope."""
    body = ApiResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=str(exception),
        errors=["inappropriate_content"],
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=body.model_dump(),
    )
