"""Application entrypoint.

Runs the FastAPI application with uvicorn. Host and port come from environment
variables so deployment settings are never hardcoded.
"""

import os

import uvicorn

from app.infrastructure.logging.logger import configure_logging, get_logger

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    host = os.getenv("APP_HOST", DEFAULT_HOST)
    port = int(os.getenv("APP_PORT", str(DEFAULT_PORT)))
    logger.info("Starting server", extra={"host": host, "port": port})
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
