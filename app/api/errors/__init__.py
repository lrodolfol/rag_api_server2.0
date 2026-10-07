"""API error-handling package.

Exposes the single entry point that registers every global exception handler on
the FastAPI application, keeping the error-to-``ApiResponse`` mapping in one
place instead of scattered across the route modules.
"""

from app.api.errors.handlers import register_exception_handlers

__all__ = ["register_exception_handlers"]
