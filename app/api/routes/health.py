"""Health-check route used to verify the application is up and responding."""

from fastapi import APIRouter

from app.api.patterns.response import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    """Return a success envelope indicating the service is healthy."""
    return ApiResponse(status_code=200, message="healthy")
