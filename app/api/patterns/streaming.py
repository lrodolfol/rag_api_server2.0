"""Server-Sent Events (SSE) streaming of ready-made answer messages.

The search flow resolves the whole answer before the stream starts, so this
module only formats and emits messages that are already available, pausing
:data:`STREAM_DELAY_SECONDS` between them to mimic a real chat. Errors never
happen inside the stream: they are raised earlier and become the standard
:class:`ApiResponse` envelope through the global exception handlers.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, Final

from fastapi.responses import StreamingResponse

STREAM_DELAY_SECONDS: Final[float] = 2
SSE_MEDIA_TYPE: Final[str] = "text/event-stream"
SSE_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}
SSE_OPENAPI_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    200: {
        "description": (
            "Server-Sent Events stream: one `data: {\"message\": \"<text>\"}` "
            "event per answer message."
        ),
        "content": {SSE_MEDIA_TYPE: {"schema": {"type": "string"}}},
    }
}


def format_event(message: str) -> str:
    """Format a single message as an SSE ``data`` event."""
    payload = json.dumps({"message": message}, ensure_ascii=False)
    return f"data: {payload}\n\n"


async def stream_messages(messages: list[str]) -> AsyncIterator[str]:
    """Yield one SSE event per message, waiting only between events."""
    for index, message in enumerate(messages):
        if index > 0:
            await asyncio.sleep(STREAM_DELAY_SECONDS)
        yield format_event(message)


def sse_response(messages: list[str]) -> StreamingResponse:
    """Build the SSE ``StreamingResponse`` that emits the given messages."""
    return StreamingResponse(
        stream_messages(messages),
        media_type=SSE_MEDIA_TYPE,
        headers=SSE_HEADERS,
    )
