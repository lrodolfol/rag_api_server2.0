"""Company registration and deletion routes.

Thin HTTP handlers that delegate the whole ingestion flow to
:class:`RegistrationService` and the deletion flow to :class:`DeletionService`. Inappropriate content raised by the service is
translated into the standard :class:`ApiResponse` envelope by the global
exception handlers (``app/api/errors``), keeping the handler itself a single
delegation and never leaking the offending text back to the client.
"""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_deletion_service, get_registration_service
from app.api.patterns.response import ApiResponse
from app.application.deletion import DeletionService
from app.application.registration import RegistrationService
from app.domain import CompanyDeletionRequest, CompanyRegistrationRequest

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


@router.delete(
    "/companies",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_company(
    deletion: CompanyDeletionRequest,
    service: DeletionService = Depends(get_deletion_service),
) -> ApiResponse:
    """Delete a company's vectors and stored record (no-op when it has none)."""
    await service.delete(deletion)
    return ApiResponse(
        status_code=status.HTTP_200_OK,
        message="Company deleted successfully",
    )
