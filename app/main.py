"""FastAPI application bootstrap.

Wires together logging, configuration and the API routers, exposing a
``create_app`` factory and a module-level ``app`` instance for ASGI servers.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import health
from app.infrastructure.config.settings import Settings, get_settings
from app.infrastructure.logging.logger import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings: Settings = application.state.settings
    logger.info("Application starting", extra={"environment": settings.environment})
    yield
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    configure_logging()
    settings = get_settings()

    application = FastAPI(
        title="RAG API Server",
        version="2.0.0",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.include_router(health.router)
    return application


app = create_app()
