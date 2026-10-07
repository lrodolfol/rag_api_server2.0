"""FastAPI application bootstrap.

Wires together logging, configuration and the API routers, exposing a
``create_app`` factory and a module-level ``app`` instance for ASGI servers.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import health, registration
from app.domain import InappropriateContentError
from app.infrastructure.logging.logger import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
    logger.info("Application starting", extra={"environment": "development"})
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    configure_logging()

    application = FastAPI(
        title="RAG API Server",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.include_router(health.router)
    application.include_router(registration.router)
    application.add_exception_handler(
        InappropriateContentError,
        registration.inappropriate_content_handler,
    )
    return application


app = create_app()
